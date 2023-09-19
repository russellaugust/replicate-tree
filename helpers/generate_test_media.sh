#!/bin/bash

# Output directory for generated media files
OUTPUT_DIR="test_media"

# If the output directory doesn't exist, create it
mkdir -p "$OUTPUT_DIR"

# Declare the dimensions, codecs, framerates, and containers you want to test
declare -a dimensions=("640x360" "1280x720" "1920x1080")
declare -a video_codecs=("libx264" "libx265" "libvpx" "none")
declare -a audio_codecs=("aac" "libvorbis" "pcm_s16le" "none")
declare -a framerates=("24" "30" "60")
declare -a containers=("mp4" "mov" "mxf" "aif" "mp3" "wav" "m4a" "m4v")

# Generate the media files
for dim in "${dimensions[@]}"; do
  for vcodec in "${video_codecs[@]}"; do
    for acodec in "${audio_codecs[@]}"; do
      for rate in "${framerates[@]}"; do
        for container in "${containers[@]}"; do
          
          # Generate a random duration for the file (between 0.1 and 1 second)
          DURATION=$(awk -v min=0.1 -v max=1 'BEGIN{srand(); print min+rand()*(max-min)}')
          
          local_vcodec=$vcodec
          local_acodec=$acodec

          # Handle specific container requirements
          case $container in
            "mp3")
              local_vcodec="none"
              local_acodec="libmp3lame"
              ;;
            "wav"|"aif")
              local_vcodec="none"
              ;;
            "m4a")
              local_vcodec="none"
              ;;
            "m4v")
              local_acodec="aac"
              ;;
          esac

          # Skip invalid combinations
          [[ $local_vcodec == "none" && $local_acodec == "none" ]] && continue

          # Generate the output file name based on the specifications
          FILENAME="${OUTPUT_DIR}/test_${dim}_${local_vcodec}_${local_acodec}_${rate}fps.${container}"

          # Check if file already exists, if so, continue to next iteration
          [[ -e $FILENAME ]] && continue

          # Generate video or audio based on codec selections
          if [[ $local_vcodec != "none" && $local_acodec != "none" ]]; then
            ffmpeg -f lavfi -i testsrc=size=${dim}:d=${DURATION} -r ${rate} \
            -c:v ${local_vcodec} -c:a ${local_acodec} -strict experimental "$FILENAME"
          elif [[ $local_vcodec != "none" ]]; then
            ffmpeg -f lavfi -i testsrc=size=${dim}:d=${DURATION} -r ${rate} \
            -c:v ${local_vcodec} "$FILENAME"
          elif [[ $local_acodec != "none" ]]; then
            ffmpeg -f lavfi -i anullsrc=d=${DURATION} -c:a ${local_acodec} "$FILENAME"
          fi
        done
      done
    done
  done
done

echo "Media generation completed. Check $OUTPUT_DIR."
