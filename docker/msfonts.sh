#!/bin/bash
set -e

exists() { which "$1" &> /dev/null ; }

FONTDIR=/usr/share/fonts/truetype

# split up to keep the download command short
DL_HOST=download.microsoft.com
DL_PATH=download/f/5/a/f5a3df76-d856-4a61-a6bd-722f52a5be26
ARCHIVE=PowerPointViewer.exe
URL="http://$DL_HOST/$DL_PATH/$ARCHIVE"

mkdir -p $FONTDIR

cd /tmp

if ! [ -e "$ARCHIVE" ] ; then
	if   exists curl  ; then curl -O "$URL"
	elif exists wget  ; then wget    "$URL"
	elif exists fetch ; then fetch   "$URL"
	fi
fi

TMPDIR=`mktemp -d`
trap 'rm -rf "$TMPDIR"' EXIT INT QUIT TERM

cabextract -L -F ppviewer.cab -d "$TMPDIR" "$ARCHIVE"

cabextract -L -F '*.TT[FC]' -d $FONTDIR "$TMPDIR/ppviewer.cab"

( cd $FONTDIR && mv cambria.ttc cambria.ttf )

fc-cache -fv $FONTDIR
