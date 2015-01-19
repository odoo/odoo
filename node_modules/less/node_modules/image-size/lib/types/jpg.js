'use strict';

// NOTE: we only support baseline and progressive JPGs here
// due to the structure of the loader class, we only get a buffer
// with a maximum size of 4096 bytes. so if the SOF marker is outside
// if this range we can't detect the file size correctly.

// TO-DO: handle all JFIFs
var validJFIFMarkers = {
  'ffdb': '0001010101', // Samsung D807 JPEG
  'ffe0': '4a46494600', // Standard JPEG
  'ffe1': '4578696600', // Camera JPEG, with EXIF data
  'ffe2': '4943435f50', // Canon EOS-1D JPEG
  'ffe3': '',           // Samsung D500 JPEG
  'ffe8': '5350494646', // SPIFF JPEG
  'ffec': '4475636b79', // Photoshop JPEG
  'ffed': '50686f746f', // Adobe JPEG, Photoshop CMYK buffer
  'ffee': '41646f6265'  // Adobe JPEG, Unrecognised (Lightroom??)
};

var red = ['\x1B[31m', '\x1B[39m'];
function isJPG (buffer) { //, filepath
  var SOIMarker = buffer.toString('hex', 0, 2);
  var JFIFMarker = buffer.toString('hex', 2, 4);

  // not a valid jpeg
  if ('ffd8' !== SOIMarker) {
    return false;
  }

  // TO-DO: validate the end-bytes of a jpeg file
  // use filepath, get the last bytes, check for ffd9
  var got = buffer.toString('hex', 6, 11);
  var expected = JFIFMarker && validJFIFMarkers[JFIFMarker];
  if (expected === '') {
    console.warn(
      red[0] +
      'this looks like a unrecognised jpeg\n' +
      'please report the issue here\n' +
      red[1],
      '\thttps://github.com/netroy/image-size/issues/new\n'
    );
    return false;
  }
  return (got === expected) || (JFIFMarker === 'ffdb');
}

function extractSize (buffer, i) {
  return {
    'height' : buffer.readUInt16BE(i),
    'width' : buffer.readUInt16BE(i + 2)
  };
}

function validateBuffer (buffer, i) {
  // index should be within buffer limits
  if (i > buffer.length) {
    throw new TypeError('Corrupt JPG, exceeded buffer limits');
  }
  // Every JPEG block must begin with a 0xFF
  if (buffer[i] !== 0xFF) {
    throw new TypeError('Invalid JPG, marker table corrupted');
  }
}

function calculate (buffer) {

  // Skip 5 chars, they are for signature
  buffer = buffer.slice(4);

  var i, next;
  while (buffer.length) {
    // read length of the next block
    i = buffer.readUInt16BE(0);

    // ensure correct format
    validateBuffer(buffer, i);

    // 0xFFC0 is baseline(SOF)
    // 0xFFC2 is progressive(SOF2)
    next = buffer[i + 1];
    if (next === 0xC0 || next === 0xC2) {
      return extractSize(buffer, i + 5);
    }

    // move to the next block
    buffer = buffer.slice(i + 2);
  }

  throw new TypeError('Invalid JPG, no size found');
}

module.exports = {
  'detect': isJPG,
  'calculate': calculate
};
