# Replicate Dummy Tree

![Logo](path_to_logo_if_you_have_one.png)

Replicate Dummy Tree is a tool tailored for the film and television industry, assisting in the archival process once a project reaches completion.

## Overview

Upon wrapping up a project, navigating through your collection of files can get cumbersome. Replicate Dummy Tree streamlines this process by creating a set of dummy files that mirror the original structure of folders and directories used during the project. This means that in the future, you can easily traverse through the folder and file structure, giving you an almost nostalgic feel of where things were originally placed - even though these aren't the original files.

## Features

- **Dummy File Creation:** Create a skeleton of your project's folder and file structure.
  
- **Embedded Metadata:** Replicate Dummy Tree isn't just about recreating structure. It allows users to embed JSON metadata into the dummy files. This is particularly valuable for crucial file types like images, videos, and audio, ensuring that you retain some essential data about the original files.

## How To Use

It's a python command line tool.

## Requirements

- You'll need `ffmpeg`, `ffprobe` and `exiftool` installed, probably through something like `brew`.

## License

This project is licensed under the [MIT License](LICENSE).

---

It's worth noting that this was only tested in macOS, and on versions of Python 3.10 in later. I can't really attest to it functioning in Linux or Windows but I don't see why it wouldn't.