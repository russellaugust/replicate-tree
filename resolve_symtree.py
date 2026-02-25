#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class Result:
    status: str
    staging_path: str
    target_path: str
    detail: str


def _safe_readlink(p: Path) -> Optional[Path]:
    """
    Return the symlink's target as a Path (may be relative), or None if not a symlink.
    """
    if not p.is_symlink():
        return None
    try:
        return Path(os.readlink(p))
    except OSError:
        return None


def _resolve_target(staging_link: Path) -> Tuple[Optional[Path], str]:
    """
    Resolve a staging symlink to an absolute path.
    Returns (abs_target_path_or_None, detail_message).
    """
    raw = _safe_readlink(staging_link)
    if raw is None:
        return None, "NOT_A_SYMLINK"

    # If raw target is relative, it is relative to the link's parent directory.
    abs_target = (staging_link.parent / raw).resolve()
    return abs_target, "OK"


def _copy_file(src: Path, dst: Path) -> None:
    """
    Copy file contents + metadata where possible.
    """
    shutil.copy2(src, dst)


def _move_file(src: Path, dst: Path) -> None:
    """
    Move a file. On same filesystem it's usually an atomic rename.
    Cross-filesystem becomes copy+delete under the hood.
    """
    shutil.move(src, dst)


def resolve_one(
    link_path: Path,
    *,
    mode: str,              # "copy" or "move"
    dry_run: bool,
    clobber: bool,
    allow_nonfile_targets: bool,
) -> Result:
    """
    Replace a symlink at link_path with its target content.
    """
    abs_target, detail = _resolve_target(link_path)
    if abs_target is None:
        return Result("SKIP_NOT_SYMLINK", str(link_path), "", detail)

    # Drift: target missing
    if not abs_target.exists():
        return Result("SKIP_MISSING_TARGET", str(link_path), str(abs_target), "Dangling symlink target missing")

    # We only expect file targets unless user allows otherwise
    if abs_target.is_dir():
        if allow_nonfile_targets:
            return Result("SKIP_DIR_TARGET", str(link_path), str(abs_target), "Directory targets not implemented")
        return Result("SKIP_DIR_TARGET", str(link_path), str(abs_target), "Target is a directory (not supported)")

    if not abs_target.is_file():
        return Result("SKIP_NONFILE_TARGET", str(link_path), str(abs_target), "Target is not a regular file")

    # Safety: only operate if link_path is actually a symlink right now
    if not link_path.is_symlink():
        return Result("SKIP_CHANGED", str(link_path), str(abs_target), "Path is no longer a symlink")

    # Prepare temp destination to avoid partial writes at the final location
    # We will:
    #   - remove symlink
    #   - write file into place
    # This is inherently non-atomic across all platforms, but is usually safe enough with logging.

    # Collision handling: if something exists and it's not the symlink itself, we should not overwrite.
    # (In normal flow, link_path exists as a symlink.)
    # But if something weird happened, we guard anyway.
    if link_path.exists() and not link_path.is_symlink():
        if not clobber:
            return Result("SKIP_DEST_EXISTS", str(link_path), str(abs_target), "Destination exists and is not a symlink")
        # clobber real file
        if dry_run:
            return Result("DRYRUN_CLOBBER", str(link_path), str(abs_target), "Would delete existing destination file")
        if link_path.is_dir():
            return Result("ERROR_DEST_IS_DIR", str(link_path), str(abs_target), "Destination is a directory")
        link_path.unlink()

    if dry_run:
        return Result(
            "DRYRUN_" + ("MOVE" if mode == "move" else "COPY"),
            str(link_path),
            str(abs_target),
            f"Would replace symlink with {'moved' if mode == 'move' else 'copied'} file",
        )

    # Remove the symlink itself (does NOT affect target)
    try:
        link_path.unlink()
    except Exception as e:
        return Result("ERROR_UNLINK", str(link_path), str(abs_target), f"Failed to remove symlink: {e}")

    # Now put the real file at the former symlink location
    try:
        if mode == "copy":
            _copy_file(abs_target, link_path)
            return Result("OK_COPY", str(link_path), str(abs_target), "Copied target into place")
        else:
            _move_file(abs_target, link_path)
            return Result("OK_MOVE", str(link_path), str(abs_target), "Moved target into place")
    except Exception as e:
        # If we failed after unlinking, we lost the symlink at link_path.
        # We try to restore the symlink as a best-effort rollback.
        try:
            # Recreate symlink pointing to original raw target
            raw = _safe_readlink(link_path)  # will be None now
            # We can’t recover the raw link content after unlink, so recreate absolute link.
            link_path.symlink_to(abs_target)
            rollback = "Restored symlink to absolute target"
        except Exception:
            rollback = "Rollback failed (symlink not restored)"
        return Result("ERROR_WRITE", str(link_path), str(abs_target), f"Failed to write file: {e}. {rollback}")


def iter_symlinks(root: Path):
    """
    Yield symlink paths under root. We do NOT follow symlinks for traversal.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dp = Path(dirpath)

        # Check symlinks that are in dirnames and filenames by inspecting full path
        # but avoid mutating dirnames; we don't followlinks anyway.
        for name in list(dirnames) + list(filenames):
            p = dp / name
            if p.is_symlink():
                yield p


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Resolve symlinks in a staging tree by replacing each symlink with the target file content."
    )
    ap.add_argument("staging_root", type=Path, help="Root of the staging tree that contains symlinks")
    ap.add_argument("--move", action="store_true", help="Move targets into place (default is copy)")
    ap.add_argument("--dry-run", action="store_true", help="Print/log what would happen without changing anything")
    ap.add_argument("--log-csv", type=Path, default=Path("resolve_symlinks_log.csv"),
                    help="CSV log output path (default: resolve_symlinks_log.csv)")
    ap.add_argument("--clobber", action="store_true",
                    help="Allow deleting an existing non-symlink destination (unsafe; default skips)")
    ap.add_argument("--include-dir-targets", action="store_true",
                    help="(Not implemented) Placeholder: directory symlink targets are skipped either way")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Print per-symlink progress and operation details")
    args = ap.parse_args()

    root = args.staging_root.resolve()
    if not root.is_dir():
        print(f"ERROR: staging_root is not a directory: {root}", file=sys.stderr)
        return 2

    mode = "move" if args.move else "copy"

    results: list[Result] = []
    counts = {}

    symlink_paths = list(iter_symlinks(root))

    if args.verbose:
        print(f"Scanning root: {root}")
        print(f"Found {len(symlink_paths)} symlink(s) to process")

    for idx, link in enumerate(symlink_paths, start=1):
        if args.verbose:
            print(f"[{idx}/{len(symlink_paths)}] {link}")

        res = resolve_one(
            link,
            mode=mode,
            dry_run=args.dry_run,
            clobber=args.clobber,
            allow_nonfile_targets=args.include_dir_targets,
        )

        if args.verbose:
            if res.target_path:
                print(f"    {res.status}: {res.staging_path} -> {res.target_path}")
            else:
                print(f"    {res.status}: {res.staging_path}")

        results.append(res)
        counts[res.status] = counts.get(res.status, 0) + 1

    # Write CSV log
    try:
        with args.log_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["status", "staging_path", "target_path", "detail"])
            for r in results:
                w.writerow([r.status, r.staging_path, r.target_path, r.detail])
    except Exception as e:
        print(f"ERROR: failed to write log CSV {args.log_csv}: {e}", file=sys.stderr)
        return 1

    # Print summary
    print(f"Staging root: {root}")
    print(f"Mode: {'MOVE' if mode=='move' else 'COPY'}  Dry-run: {args.dry_run}")
    print(f"Symlinks found: {len(results)}")
    for k in sorted(counts.keys()):
        print(f"  {k}: {counts[k]}")
    print(f"Log: {args.log_csv.resolve()}")

    # Nonzero exit if errors
    if any(k.startswith("ERROR") for k in counts):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())