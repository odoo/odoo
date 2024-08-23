#!/bin/bash

for filename in ../../addons/*; do
    if [[ -d "$filename" ]]; then
       if [[ "$filename" != "../../setup" ]]; then
           echo "$filename"
           ln -s "$filename"
       fi 
    fi
done

