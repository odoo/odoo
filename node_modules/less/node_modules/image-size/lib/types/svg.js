'use strict';

var svgReg = /<svg[^>]+[^>]*>/;
function isSVG (buffer) {
  return svgReg.test(buffer);
}

var extractorRegExps = {
  'root': /<svg [^>]+>/,
  'width': /(^|\s)width\s*=\s*"(.+?)"/i,
  'height': /(^|\s)height\s*=\s*"(.+?)"/i,
  'viewbox': /(^|\s)viewbox\s*=\s*"(.+?)"/i
};

function getRatio (viewbox) {
  var ratio = 1;
  if (viewbox && viewbox[2]) {
    var dim = viewbox[2].split(/\s/g);
    if (dim.length === 4) {
      dim = dim.map(function (i) {
        return parseInt(i, 10);
      });
      ratio = (dim[2] - dim[0]) / (dim[3] - dim[1]);
    }
  }
  return ratio;
}

function parse (buffer) {
  var body = buffer.toString().replace(/[\r\n\s]+/g, ' ');
  var section = body.match(extractorRegExps.root);
  var root = section && section[0];
  if (root) {
    var width = root.match(extractorRegExps.width);
    var height = root.match(extractorRegExps.height);
    var viewbox = root.match(extractorRegExps.viewbox);
    var ratio = getRatio(viewbox);
    return {
      'width': parseInt(width && width[2], 10) || 0,
      'height': parseInt(height && height[2], 10) || 0,
      'ratio': ratio
    };
  }
}

function calculate (buffer) {

  var parsed = parse(buffer);
  var width = parsed.width;
  var height = parsed.height;
  var ratio = parsed.ratio;

  if (width && height) {
    return { 'width': width, 'height': height };
  } else {
    if (width) {
      return { 'width': width, 'height': Math.floor(width / ratio) };
    } else if (height) {
      return { 'width': Math.floor(height * ratio), 'height': height };
    } else {
      throw new TypeError('invalid svg');
    }
  }
}

module.exports = {
  'detect': isSVG,
  'calculate': calculate
};
