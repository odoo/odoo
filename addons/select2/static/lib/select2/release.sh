#!/bin/bash
set -e

echo -n "Enter the version for this release: "

read ver

if [ ! $ver ]; then 
	echo "Invalid version."
	exit
fi

name="select2"
js="$name.js"
mini="$name.min.js"
css="$name.css"
release="$name-$ver"
releasedir="/tmp/$release"
tag="release-$ver"
branch="build-$ver"
curbranch=`git branch | grep "*" | sed "s/* //"`
timestamp=$(date)
tokens="s/@@ver@@/$ver/g;s/\@@timestamp@@/$timestamp/g"
remote="github"

git branch "$branch"
git checkout "$branch"

echo "Tokenizing..."

find . -name "$js" | xargs sed -i -e "$tokens"
find . -name "$css" | xargs sed -i -e "$tokens"

git add "$js"
git add "$css"

echo "Minifying..."

echo "/*" > "$mini"
cat LICENSE | sed "$tokens" >> "$mini"
echo "*/" >> "$mini"

curl -s \
	-d compilation_level=SIMPLE_OPTIMIZATIONS \
	-d output_format=text \
	-d output_info=compiled_code \
	--data-urlencode "js_code@$js" \
	http://closure-compiler.appspot.com/compile \
	>> "$mini"

git add "$mini"
	
git commit -m "release $ver"

echo "Tagging..."

git tag -a "$tag" -m "tagged version $ver"
git push "$remote" --tags

echo "Archiving..."

rm -rf "$releasedir"
mkdir "$releasedir"

cp $name.* "$releasedir"
cp spinner.gif "$releasedir"
cp README.* "$releasedir"

zip -r "$releasedir.zip" "$releasedir"
rm -rf "$releasedir"

echo "Cleaning Up..."

git checkout "$curbranch"
git branch -D "$branch"

echo "Done. Release archive created: $releasedir.zip"
