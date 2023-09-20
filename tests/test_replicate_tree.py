import dummy_tree
import pytest
from unittest.mock import patch
from pathlib import Path


def test_main():
    assert 1==1
    
def test_parse_arguments():
    # Mock the command-line arguments
    source = '/Volumes/Drive1/some/place'
    destination = '/Volumes/Drive 2/some/destination'
    
    # Test that the source and destination are parsed correctly
    with patch('sys.argv', ['replicate', '-s', source, '-d', destination]):
        args = dummy_tree.parse_arguments()
        assert args.source == Path(source)
        assert args.destination == Path(destination)
        
    # Raise error if source or destination is not specified
    with patch('sys.argv', ['replicate', '-s', source]),\
         pytest.raises(SystemExit):
            args = dummy_tree.parse_arguments()

def test_touch_and_ffprobe_videofile(tmp_path:Path):
    src_file = Path('tests/tree/audio/manually generated/A01.DF212D1FD23BA.mxf')
    
    dst_base = tmp_path / "FAKE_RAID2"
    dst_file = dst_base / src_file
    
    dummy_tree.touch_and_ffprobe(src_file, dst_file, True)
    
    assert dst_file.stat().st_size > 0
    
def test_supported_formats_from_ffmpeg():
    result = dummy_tree.supported_input_formats()
    assert isinstance(result, list)
    
def test_replicate_directories_files_that_are_never_touched_or_created(tmp_path:Path):
    with patch('dummy_tree.touch_and_ffprobe', return_value=None):
        src_base = Path('tests/tree')
        dst_base = tmp_path / "FAKE_RAID2"
        
        dummy_tree.process_directory(src_base, dst_base)
        
        assert dst_base.exists() and dst_base.is_dir()
    
def test_replicate_directories_without_dummy_data(tmp_path:Path):

    src_base = Path('tests/tree')
    dst_base = tmp_path / "FAKE_RAID2"

    dummy_tree.process_directory(src_base, dst_base)
    
    # Check the size of the directory tree
    dst_base_size = sum(f.stat().st_size for f in dst_base.glob('**/*') if f.is_file())
    
    # if the size is 0, then we know that the dummy files were not created
    assert dst_base_size == 0
    
def test_replicate_directories_and_store_dummy_data(tmp_path:Path):

    src_base = Path('tests/tree')
    dst_base = tmp_path / "FAKE_RAID2"

    dummy_tree.process_directory(src_base, dst_base, metadata=True)
    
    # Check the size of the directory tree
    dst_base_size = sum(f.stat().st_size for f in dst_base.glob('**/*') if f.is_file())
    
    # if the size is greater than 0, then we know that the dummy files were created
    assert dst_base_size > 0

def test_replicate_directories_and_store_dummy_data(tmp_path:Path):

    src_base = Path('tests/tree')
    dst_base = tmp_path / "FAKE_RAID2"

    dummy_tree.process_directory(src_base, dst_base, files=False)
    
    # Check the size of the directory tree
    dst_base_size = sum(f.stat().st_size for f in dst_base.glob('**/*') if f.is_file())
    
    # Count number of files and not directories
    dst_base_files = sum(f.is_file() for f in dst_base.glob('**/*'))

    # if the number of files is zero, we know that the dummy files were not created
    assert dst_base_size == 0
    assert dst_base_files == 0
    
def test_extract_media_metadata_video():
    src_file = Path('tests/tree/video/test_1920x1080_none_pcm_s16le_30fps.mov')
    result = dummy_tree.extract_media_metadata(src_file)
    assert isinstance(result, dict)

def test_extract_media_metadata_audio():
    src_file = Path('tests/tree/audio/manually generated/A01.DF212D1FD23BA.mxf')
    result = dummy_tree.extract_media_metadata(src_file)
    assert isinstance(result, dict)
    
def test_extract_image_metadata():
    folder_path = Path('tests/tree/images')
    
    # Ensure the folder exists
    assert folder_path.exists() and folder_path.is_dir()

    for src_file in folder_path.iterdir():
        # Optionally: You can check if src_file is a file before testing
        if src_file.is_file():
            result = dummy_tree.extract_image_metadata(src_file)
            assert isinstance(result, dict)
    
# TODO Will need to mock subprocess.run - also need to add exiftool
# def test_ffmpeg_and_ffprobe_are_installed():
    
#     ffmpeg_installed = dummy_tree.check_installation("ffmpeg")
#     assert isinstance(ffmpeg_installed, bool)

#     with patch('dummy_tree.subprocess.run', return_value="ffprobe"):
#         ffprobe_installed = dummy_tree.check_installation("ffprobe")
#         assert isinstance(ffprobe_installed, bool)