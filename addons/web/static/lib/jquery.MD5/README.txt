jQuery MD5 Plugin
=================

Usage
-----
Create (hex-encoded) MD5 hash of a given string value:
    var md5 = $.md5('value');

Create (hex-encoded) HMAC-MD5 hash of a given string value and key:
    var md5 = $.md5('value', 'key');
    
Create raw MD5 hash of a given string value:
    var md5 = $.md5('value', null, true);

Create raw HMAC-MD5 hash of a given string value and key:
    var md5 = $.md5('value', 'key', true);

Requirements
------------
None.

If jQuery is not available, the md5 function will be added to the global object:
    var md5 = md5('value');

License
-------
Released under the MIT license:
http://creativecommons.org/licenses/MIT/

Source Code & Download
----------------------
https://github.com/blueimp/jQuery-MD5
