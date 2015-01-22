#!/bin/sh
git add --all
git commit -a -m "prototype changed"
git pull
git mergetool
git push
