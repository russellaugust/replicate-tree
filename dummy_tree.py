from pathlib import Path
import argparse, subprocess, json

def check_installation(tool_name):
    try:
        # Using "--version" to check if the tool is installed
        result = subprocess.run([tool_name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # If we get here without an exception, the tool is installed. 
        # Additionally, check the output to ensure it's not an unrelated command.
        if tool_name in result.stdout:
            return True
        else:
            return False
    except FileNotFoundError:
        # If subprocess raises a FileNotFoundError, the tool is not installed.
        return False
    

def extract_image_metadata(src_file: Path) -> dict:
    try:
        # Get metadata in JSON format from exiftool
        result = subprocess.run(
            ["exiftool", "-j", str(src_file)], 
            capture_output=True, text=True, check=True)
        # exiftool outputs a JSON list, so we take the first element
        return json.loads(result.stdout)[0]
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return {}
    
def extract_media_metadata(src_file: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", 
            "-show_format", "-show_streams", str(src_file)], 
        capture_output=True, text=True, check=True)
    
    if result.returncode == 0:
        pass
    else:
        print(f"ffprobe encountered an error with {src_file}")
        
    return json.loads(result.stdout)
    

def supported_input_formats():
    try:
        result = subprocess.run(["ffmpeg", "-formats"], capture_output=True, 
                                text=True, check=True)
        lines = result.stdout.splitlines()
        formats = []

        for line in lines:
            if line.startswith(" D"):
                tokens = line.split()
                if ',' in tokens[1]:
                    # A couple formats have multiple extensions
                    formats.extend(tokens[1].split(','))
                else:
                    formats.append(tokens[1])
        return formats
    except (subprocess.CalledProcessError, IndexError) as e:
        print(f"Error occurred: {e}")
        return []
            

def touch_and_ffprobe(src_file: Path, dst_file: Path, metadata=False):
    """
    Touch the file in the destination directory and run ffprobe if necessary.
    """
    # Use touch to create an empty file at the destination
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.touch()
    
    # # This used to get supported file formats directly from ffmpeg but its dangerous and slow.
    # formats_video_audio = supported_input_formats()
    
    # Generate a list of video and audio extensions
    video_extensions = set(['mp4','m4v','mkv','webm','mov','avi','wmv','mpg','mpeg','m2v','m2p','m2ts','mts','ts','mxf','ogg','oga','ogv','ogx','opus','3gp','3g2','amv','asf','nut','rm','swf','vob','wav','lxf','gxf','voc','w64','wma','wv','webm','yuv','rmvb','drc','gifv','mng','mov','qt','wmv','yuv','rmvb','drc','gifv','mng','mov','qt','wmv','yuv'])
    audio_extensions = set(['mp3','m4a','aac','flac','ogg','oga','opus','wma','wav','wv','webm'])
    videoaudio_extensions = video_extensions | audio_extensions
    
    # Generate a set of image extensions
    image_extensions = set(['jpg','jpeg','png','gif','webp','tiff','tif','psd','raw','bmp','heif','svg','ai','eps','pdf'])
    
    suffix = src_file.suffix[1:].lower()
    
    # Check if file extension matches one of the types for which we want ffprobe data
    if suffix in videoaudio_extensions and metadata:
        # Run ffprobe with JSON output format and write its output to the touched file
        with dst_file.open('w') as f:
            result = json.dump(extract_media_metadata(src_file), f, indent=4)

    elif suffix in image_extensions and metadata:
        # Run exiftool with JSON output format and write its output to the touched file
        with dst_file.open('w') as f:
            result = json.dump(extract_image_metadata(src_file), f, indent=4)
            


def process_directory(src_dir:Path, dst_dir:Path, files:bool=True, metadata:bool=False):
    """
    Recursively replicate the folder structure from source_dir to dest_dir, 
    touch files, and run ffprobe on certain file types.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    for source_item in src_dir.iterdir():
        dest_item = dst_dir / source_item.name
        
        if source_item.is_dir():
            process_directory(source_item, dest_item, files=files, metadata=metadata)
        elif files:
            touch_and_ffprobe(source_item, dest_item, metadata=metadata)
            

def parse_arguments():
    parser = argparse.ArgumentParser(description='Replicate a directory tree')
    
    parser.add_argument('-s', '--source', 
                        type=Path, 
                        required=True,
                        help='Source directory')
    parser.add_argument('-d', '--destination', 
                        type=Path, 
                        required=True,
                        help='Destination directory')
    parser.add_argument('-f', '--files', 
                        action='store_true',
                        help='Only rebuild the folder structure, excluding all files.')
    parser.add_argument('-p', '--metdata', 
                        action='store_true',
                        help='Will store the metadata data as json inside the dummy file.')
    
    return parser.parse_args()

# Write boilerplate code for the main function and argparse
def main():
    
    args = parse_arguments()

    src = Path(args.source)
    dst = Path(args.destination)

    process_directory(src, dst, args.files, args.metdata)
    
if __name__ == '__main__':
    main()