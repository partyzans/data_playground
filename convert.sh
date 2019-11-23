#!/bin/bash

OIFS="$IFS"
IFS=$'\n'

for file in `find "$1" -type f`
do
  echo "$file"

  extname=`basename "$file" | sed 's/^\([^.]*\)\.\(.*\)$/\2/g'`
  if [ "$extname" == "png" ]; then
    continue
  fi

  mkdir -p "$1"/pngs
  convert "$file" -resize 1024x768 "$1/$basename.png"
  convert "$file" "$1/$basename.png"
done


IFS="$OIFS"
