[![Build Status](https://travis-ci.org/netroy/image-size.png?branch=master)](https://travis-ci.org/netroy/image-size)
[![NPM Downloads](http://img.shields.io/npm/dm/image-size.svg)](https://npmjs.org/package/image-size)
[![Gittip](http://img.shields.io/gittip/netroy.svg)](https://www.gittip.com/netroy/)

[![Coverage Status](https://coveralls.io/repos/netroy/image-size/badge.png?branch=master)](https://coveralls.io/r/netroy/image-size?branch=master)
[![Technical debt analysis](https://www.sidekickjs.com/r/netroy/image-size/status_badge.svg)](https://www.sidekickjs.com/r/netroy/image-size)
[![Code Climate](https://codeclimate.com/github/netroy/image-size.png)](https://codeclimate.com/github/netroy/image-size)
[![Dependency Status](https://gemnasium.com/netroy/image-size.png)](https://gemnasium.com/netroy/image-size)

#### Instalation

`npm install image-size`

#### Usage

```javascript
var sizeOf = require('image-size');
var dimensions = sizeOf('images/funny-cats.png');
console.log(dimensions.width, dimensions.height);
```

##### Async version
```javascript
var sizeOf = require('image-size');
sizeOf('images/funny-cats.png', function (err, dimensions) {
  console.log(dimensions.width, dimensions.height);
});
```

##### Using a url
```javascript
var url = require('url');
var http = require('http');

var sizeOf = require('image-size');

var imgUrl = 'http://my-amazing-website.com/image.jpeg';
var options = url.parse(imgUrl);

http.get(options, function (response) {
  var chunks = [];
  response.on('data', function (chunk) {
    chunks.push(chunk);
  }).on('end', function() {
    var buffer = Buffer.concat(chunks);
    console.log(sizeOf(buffer));
  });
});
```
You can optionally check the buffer lengths & stop downloading the image after a few kilobytes.
**You don't need to download the entire image**

#### Supported formats
* BMP
* GIF
* JPEG
* PNG
* PSD
* TIFF
* WebP
* SVG

##### Upcoming
* SWF

##### Credits
not a direct port, but an attempt to have something like
[dabble's imagesize](https://github.com/dabble/imagesize/blob/master/lib/image_size.rb) as a node module.

##### [Contributors](Contributors.md)
