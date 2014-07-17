// Input 0
/*


 Copyright (C) 2012 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
var core={},gui={},xmldom={},odf={},ops={};
// Input 1
function Runtime(){}Runtime.ByteArray=function(f){};Runtime.prototype.getVariable=function(f){};Runtime.prototype.toJson=function(f){};Runtime.prototype.fromJson=function(f){};Runtime.ByteArray.prototype.slice=function(f,h){};Runtime.ByteArray.prototype.length=0;Runtime.prototype.byteArrayFromArray=function(f){};Runtime.prototype.byteArrayFromString=function(f,h){};Runtime.prototype.byteArrayToString=function(f,h){};Runtime.prototype.concatByteArrays=function(f,h){};
Runtime.prototype.read=function(f,h,c,g){};Runtime.prototype.readFile=function(f,h,c){};Runtime.prototype.readFileSync=function(f,h){};Runtime.prototype.loadXML=function(f,h){};Runtime.prototype.writeFile=function(f,h,c){};Runtime.prototype.isFile=function(f,h){};Runtime.prototype.getFileSize=function(f,h){};Runtime.prototype.deleteFile=function(f,h){};Runtime.prototype.log=function(f,h){};Runtime.prototype.setTimeout=function(f,h){};Runtime.prototype.clearTimeout=function(f){};
Runtime.prototype.libraryPaths=function(){};Runtime.prototype.type=function(){};Runtime.prototype.getDOMImplementation=function(){};Runtime.prototype.parseXML=function(f){};Runtime.prototype.getWindow=function(){};Runtime.prototype.assert=function(f,h,c){};var IS_COMPILED_CODE=!0;
Runtime.byteArrayToString=function(f,h){function c(b){var a="",n,e=b.length;for(n=0;n<e;n+=1)a+=String.fromCharCode(b[n]&255);return a}function g(b){var a="",n,e=b.length,d,c,l,r;for(n=0;n<e;n+=1)d=b[n],128>d?a+=String.fromCharCode(d):(n+=1,c=b[n],194<=d&&224>d?a+=String.fromCharCode((d&31)<<6|c&63):(n+=1,l=b[n],224<=d&&240>d?a+=String.fromCharCode((d&15)<<12|(c&63)<<6|l&63):(n+=1,r=b[n],240<=d&&245>d&&(d=(d&7)<<18|(c&63)<<12|(l&63)<<6|r&63,d-=65536,a+=String.fromCharCode((d>>10)+55296,(d&1023)+56320)))));
return a}var b;"utf8"===h?b=g(f):("binary"!==h&&this.log("Unsupported encoding: "+h),b=c(f));return b};Runtime.getVariable=function(f){try{return eval(f)}catch(h){}};Runtime.toJson=function(f){return JSON.stringify(f)};Runtime.fromJson=function(f){return JSON.parse(f)};Runtime.getFunctionName=function(f){return void 0===f.name?(f=/function\s+(\w+)/.exec(f))&&f[1]:f.name};
function BrowserRuntime(f){function h(a,n){var e,d,b;void 0!==n?b=a:n=a;f?(d=f.ownerDocument,b&&(e=d.createElement("span"),e.className=b,e.appendChild(d.createTextNode(b)),f.appendChild(e),f.appendChild(d.createTextNode(" "))),e=d.createElement("span"),0<n.length&&"<"===n[0]?e.innerHTML=n:e.appendChild(d.createTextNode(n)),f.appendChild(e),f.appendChild(d.createElement("br"))):console&&console.log(n);"alert"===b&&alert(n)}function c(a,n,e){function d(){var d;4===c.readyState&&(0!==c.status||c.responseText?
200===c.status||0===c.status?(d="binary"===n?null!==c.responseBody&&"undefined"!==String(typeof VBArray)?(new VBArray(c.responseBody)).toArray():g.byteArrayFromString(c.responseText,"binary"):c.responseText,b[a]=d,e(null,d)):e(c.responseText||c.statusText):e("File "+a+" is empty."))}if(b.hasOwnProperty(a))e(null,b[a]);else{var c=new XMLHttpRequest;c.open("GET",a,!0);c.onreadystatechange=d;c.overrideMimeType&&("binary"!==n?c.overrideMimeType("text/plain; charset="+n):c.overrideMimeType("text/plain; charset=x-user-defined"));
try{c.send(null)}catch(l){e(l.message)}}}var g=this,b={},p=window.ArrayBuffer&&window.Uint8Array;p&&(Uint8Array.prototype.slice=function(a,n){void 0===n&&(void 0===a&&(a=0),n=this.length);var e=this.subarray(a,n),d,b;n-=a;d=new Uint8Array(new ArrayBuffer(n));for(b=0;b<n;b+=1)d[b]=e[b];return d});this.ByteArray=p?function(a){return new Uint8Array(new ArrayBuffer(a))}:function(a){var n=[];n.length=a;return n};this.concatByteArrays=p?function(a,n){var e,d=a.length,b=n.length,l=new this.ByteArray(d+b);
for(e=0;e<d;e+=1)l[e]=a[e];for(e=0;e<b;e+=1)l[e+d]=n[e];return l}:function(a,b){return a.concat(b)};this.byteArrayFromArray=function(a){return a.slice()};this.byteArrayFromString=function(a,b){var e;if("utf8"===b){e=a.length;var d,c,l,r=0;for(c=0;c<e;c+=1)l=a.charCodeAt(c),r+=1+(128<l)+(2048<l);d=new g.ByteArray(r);for(c=r=0;c<e;c+=1)l=a.charCodeAt(c),128>l?(d[r]=l,r+=1):2048>l?(d[r]=192|l>>>6,d[r+1]=128|l&63,r+=2):(d[r]=224|l>>>12&15,d[r+1]=128|l>>>6&63,d[r+2]=128|l&63,r+=3)}else for("binary"!==
b&&g.log("unknown encoding: "+b),e=a.length,d=new g.ByteArray(e),c=0;c<e;c+=1)d[c]=a.charCodeAt(c)&255;return e=d};this.byteArrayToString=Runtime.byteArrayToString;this.getVariable=Runtime.getVariable;this.fromJson=Runtime.fromJson;this.toJson=Runtime.toJson;this.readFile=c;this.read=function(a,n,e,d){function c(){var k;4===l.readyState&&(0!==l.status||l.responseText?200===l.status||0===l.status?(l.response?(k=l.response,k=new Uint8Array(k)):k=null!==l.responseBody&&"undefined"!==String(typeof VBArray)?
(new VBArray(l.responseBody)).toArray():g.byteArrayFromString(l.responseText,"binary"),b[a]=k,d(null,k.slice(n,n+e))):d(l.responseText||l.statusText):d("File "+a+" is empty."))}if(b.hasOwnProperty(a))d(null,b[a].slice(n,n+e));else{var l=new XMLHttpRequest;l.open("GET",a,!0);l.onreadystatechange=c;l.overrideMimeType&&l.overrideMimeType("text/plain; charset=x-user-defined");l.responseType="arraybuffer";try{l.send(null)}catch(r){d(r.message)}}};this.readFileSync=function(a,b){var e=new XMLHttpRequest,
d;e.open("GET",a,!1);e.overrideMimeType&&("binary"!==b?e.overrideMimeType("text/plain; charset="+b):e.overrideMimeType("text/plain; charset=x-user-defined"));try{if(e.send(null),200===e.status||0===e.status)d=e.responseText}catch(c){}return d};this.writeFile=function(a,n,e){b[a]=n;var d=new XMLHttpRequest;d.open("PUT",a,!0);d.onreadystatechange=function(){4===d.readyState&&(0!==d.status||d.responseText?200<=d.status&&300>d.status||0===d.status?e(null):e("Status "+String(d.status)+": "+d.responseText||
d.statusText):e("File "+a+" is empty."))};n=n.buffer&&!d.sendAsBinary?n.buffer:g.byteArrayToString(n,"binary");try{d.sendAsBinary?d.sendAsBinary(n):d.send(n)}catch(c){g.log("HUH? "+c+" "+n),e(c.message)}};this.deleteFile=function(a,n){delete b[a];var e=new XMLHttpRequest;e.open("DELETE",a,!0);e.onreadystatechange=function(){4===e.readyState&&(200>e.status&&300<=e.status?n(e.responseText):n(null))};e.send(null)};this.loadXML=function(a,b){var e=new XMLHttpRequest;e.open("GET",a,!0);e.overrideMimeType&&
e.overrideMimeType("text/xml");e.onreadystatechange=function(){4===e.readyState&&(0!==e.status||e.responseText?200===e.status||0===e.status?b(null,e.responseXML):b(e.responseText):b("File "+a+" is empty."))};try{e.send(null)}catch(d){b(d.message)}};this.isFile=function(a,b){g.getFileSize(a,function(a){b(-1!==a)})};this.getFileSize=function(a,b){var e=new XMLHttpRequest;e.open("HEAD",a,!0);e.onreadystatechange=function(){if(4===e.readyState){var d=e.getResponseHeader("Content-Length");d?b(parseInt(d,
10)):c(a,"binary",function(d,a){d?b(-1):b(a.length)})}};e.send(null)};this.log=h;this.assert=function(a,b,e){if(!a)throw h("alert","ASSERTION FAILED:\n"+b),e&&e(),b;};this.setTimeout=function(a,b){return setTimeout(function(){a()},b)};this.clearTimeout=function(a){clearTimeout(a)};this.libraryPaths=function(){return["lib"]};this.setCurrentDirectory=function(){};this.type=function(){return"BrowserRuntime"};this.getDOMImplementation=function(){return window.document.implementation};this.parseXML=function(a){return(new DOMParser).parseFromString(a,
"text/xml")};this.exit=function(a){h("Calling exit with code "+String(a)+", but exit() is not implemented.")};this.getWindow=function(){return window}}
function NodeJSRuntime(){function f(a,e,d){a=g.resolve(b,a);"binary"!==e?c.readFile(a,e,d):c.readFile(a,null,d)}var h=this,c=require("fs"),g=require("path"),b="",p,a;this.ByteArray=function(a){return new Buffer(a)};this.byteArrayFromArray=function(a){var e=new Buffer(a.length),d,b=a.length;for(d=0;d<b;d+=1)e[d]=a[d];return e};this.concatByteArrays=function(a,e){var d=new Buffer(a.length+e.length);a.copy(d,0,0);e.copy(d,a.length,0);return d};this.byteArrayFromString=function(a,e){return new Buffer(a,
e)};this.byteArrayToString=function(a,e){return a.toString(e)};this.getVariable=Runtime.getVariable;this.fromJson=Runtime.fromJson;this.toJson=Runtime.toJson;this.readFile=f;this.loadXML=function(a,e){f(a,"utf-8",function(d,a){if(d)return e(d);e(null,h.parseXML(a))})};this.writeFile=function(a,e,d){a=g.resolve(b,a);c.writeFile(a,e,"binary",function(a){d(a||null)})};this.deleteFile=function(a,e){a=g.resolve(b,a);c.unlink(a,e)};this.read=function(a,e,d,f){a=g.resolve(b,a);c.open(a,"r+",666,function(a,
b){if(a)f(a);else{var k=new Buffer(d);c.read(b,k,0,d,e,function(d){c.close(b);f(d,k)})}})};this.readFileSync=function(a,e){return e?"binary"===e?c.readFileSync(a,null):c.readFileSync(a,e):""};this.isFile=function(a,e){a=g.resolve(b,a);c.stat(a,function(d,a){e(!d&&a.isFile())})};this.getFileSize=function(a,e){a=g.resolve(b,a);c.stat(a,function(d,a){d?e(-1):e(a.size)})};this.log=function(a,e){var d;void 0!==e?d=a:e=a;"alert"===d&&process.stderr.write("\n!!!!! ALERT !!!!!\n");process.stderr.write(e+
"\n");"alert"===d&&process.stderr.write("!!!!! ALERT !!!!!\n")};this.assert=function(a,e,d){a||(process.stderr.write("ASSERTION FAILED: "+e),d&&d())};this.setTimeout=function(a,e){return setTimeout(function(){a()},e)};this.clearTimeout=function(a){clearTimeout(a)};this.libraryPaths=function(){return[__dirname]};this.setCurrentDirectory=function(a){b=a};this.currentDirectory=function(){return b};this.type=function(){return"NodeJSRuntime"};this.getDOMImplementation=function(){return a};this.parseXML=
function(a){return p.parseFromString(a,"text/xml")};this.exit=process.exit;this.getWindow=function(){return null};p=new (require("xmldom").DOMParser);a=h.parseXML("<a/>").implementation}
function RhinoRuntime(){function f(a,b){var e;void 0!==b?e=a:b=a;"alert"===e&&print("\n!!!!! ALERT !!!!!");print(b);"alert"===e&&print("!!!!! ALERT !!!!!")}var h=this,c=Packages.javax.xml.parsers.DocumentBuilderFactory.newInstance(),g,b,p="";c.setValidating(!1);c.setNamespaceAware(!0);c.setExpandEntityReferences(!1);c.setSchema(null);b=Packages.org.xml.sax.EntityResolver({resolveEntity:function(a,b){var e=new Packages.java.io.FileReader(b);return new Packages.org.xml.sax.InputSource(e)}});g=c.newDocumentBuilder();
g.setEntityResolver(b);this.ByteArray=function(a){return[a]};this.byteArrayFromArray=function(a){return a};this.byteArrayFromString=function(a,b){var e=[],d,c=a.length;for(d=0;d<c;d+=1)e[d]=a.charCodeAt(d)&255;return e};this.byteArrayToString=Runtime.byteArrayToString;this.getVariable=Runtime.getVariable;this.fromJson=Runtime.fromJson;this.toJson=Runtime.toJson;this.concatByteArrays=function(a,b){return a.concat(b)};this.loadXML=function(a,b){var e=new Packages.java.io.File(a),d;try{d=g.parse(e)}catch(c){print(c);
b(c);return}b(null,d)};this.readFile=function(a,b,e){p&&(a=p+"/"+a);var d=new Packages.java.io.File(a),c="binary"===b?"latin1":b;d.isFile()?(a=readFile(a,c),"binary"===b&&(a=h.byteArrayFromString(a,"binary")),e(null,a)):e(a+" is not a file.")};this.writeFile=function(a,b,e){p&&(a=p+"/"+a);a=new Packages.java.io.FileOutputStream(a);var d,c=b.length;for(d=0;d<c;d+=1)a.write(b[d]);a.close();e(null)};this.deleteFile=function(a,b){p&&(a=p+"/"+a);(new Packages.java.io.File(a))["delete"]()?b(null):b("Could not delete "+
a)};this.read=function(a,b,e,d){p&&(a=p+"/"+a);var c;c=a;var l="binary";(new Packages.java.io.File(c)).isFile()?("binary"===l&&(l="latin1"),c=readFile(c,l)):c=null;c?d(null,this.byteArrayFromString(c.substring(b,b+e),"binary")):d("Cannot read "+a)};this.readFileSync=function(a,b){return b?readFile(a,b):""};this.isFile=function(a,b){p&&(a=p+"/"+a);var e=new Packages.java.io.File(a);b(e.isFile())};this.getFileSize=function(a,b){p&&(a=p+"/"+a);var e=new Packages.java.io.File(a);b(e.length())};this.log=
f;this.assert=function(a,b,e){a||(f("alert","ASSERTION FAILED: "+b),e&&e())};this.setTimeout=function(a){a();return 0};this.clearTimeout=function(){};this.libraryPaths=function(){return["lib"]};this.setCurrentDirectory=function(a){p=a};this.currentDirectory=function(){return p};this.type=function(){return"RhinoRuntime"};this.getDOMImplementation=function(){return g.getDOMImplementation()};this.parseXML=function(a){return g.parse(a)};this.exit=quit;this.getWindow=function(){return null}}
var runtime=function(){return"undefined"!==String(typeof window)?new BrowserRuntime(window.document.getElementById("logoutput")):"undefined"!==String(typeof require)?new NodeJSRuntime:new RhinoRuntime}();
(function(){function f(c){var b=c[0],f;f=eval("if (typeof "+b+" === 'undefined') {eval('"+b+" = {};');}"+b);for(b=1;b<c.length-1;b+=1)f=f.hasOwnProperty(c[b])?f[c[b]]:f[c[b]]={};return f[c[c.length-1]]}var h={},c={};runtime.loadClass=function(g){function b(a){a=a.replace(/\./g,"/")+".js";var d=runtime.libraryPaths(),b,l,r;runtime.currentDirectory&&d.push(runtime.currentDirectory());for(b=0;b<d.length;b+=1){l=d[b];if(!c.hasOwnProperty(l))try{r=runtime.readFileSync(d[b]+"/manifest.js","utf8"),c[l]=
r&&r.length?eval(r):null}catch(k){c[l]=null,runtime.log("Cannot load manifest for "+l+".")}r=null;if((l=c[l])&&l.indexOf&&-1!==l.indexOf(a))return d[b]+"/"+a}return null}function p(a){var d,c;c=b(a);if(!c)throw a+" is not listed in any manifest.js.";try{d=runtime.readFileSync(c,"utf8")}catch(l){throw runtime.log("Error loading "+a+" "+l),l;}if(void 0===d)throw"Cannot load class "+a;d=d+("\n//# sourceURL="+c)+("\n//@ sourceURL="+c);try{d=eval(a+" = eval(code);")}catch(r){throw runtime.log("Error loading "+
a+" "+r),r;}return d}if(!IS_COMPILED_CODE&&!h.hasOwnProperty(g)){var a=g.split("."),n;n=f(a);if(!n&&(n=p(g),!n||Runtime.getFunctionName(n)!==a[a.length-1]))throw runtime.log("Loaded code is not for "+a[a.length-1]),"Loaded code is not for "+a[a.length-1];h[g]=!0}}})();
(function(f){function h(c){if(c.length){var g=c[0];runtime.readFile(g,"utf8",function(b,f){function a(){var d;(d=eval(e))&&runtime.exit(d)}var h="",e=f;-1!==g.indexOf("/")&&(h=g.substring(0,g.indexOf("/")));runtime.setCurrentDirectory(h);b||null===e?(runtime.log(b),runtime.exit(1)):a.apply(null,c)})}}f=f?Array.prototype.slice.call(f):[];"NodeJSRuntime"===runtime.type()?h(process.argv.slice(2)):"RhinoRuntime"===runtime.type()?h(f):h(f.slice(1))})("undefined"!==String(typeof arguments)&&arguments);
// Input 2
core.Base64=function(){function f(d){var a=[],b,e=d.length;for(b=0;b<e;b+=1)a[b]=d.charCodeAt(b)&255;return a}function h(d){var a,b="",e,l=d.length-2;for(e=0;e<l;e+=3)a=d[e]<<16|d[e+1]<<8|d[e+2],b+=m[a>>>18],b+=m[a>>>12&63],b+=m[a>>>6&63],b+=m[a&63];e===l+1?(a=d[e]<<4,b+=m[a>>>6],b+=m[a&63],b+="=="):e===l&&(a=d[e]<<10|d[e+1]<<2,b+=m[a>>>12],b+=m[a>>>6&63],b+=m[a&63],b+="=");return b}function c(a){a=a.replace(/[^A-Za-z0-9+\/]+/g,"");var d=[],b=a.length%4,e,l=a.length,k;for(e=0;e<l;e+=4)k=(q[a.charAt(e)]||
0)<<18|(q[a.charAt(e+1)]||0)<<12|(q[a.charAt(e+2)]||0)<<6|(q[a.charAt(e+3)]||0),d.push(k>>16,k>>8&255,k&255);d.length-=[0,0,2,1][b];return d}function g(a){var d=[],b,e=a.length,l;for(b=0;b<e;b+=1)l=a[b],128>l?d.push(l):2048>l?d.push(192|l>>>6,128|l&63):d.push(224|l>>>12&15,128|l>>>6&63,128|l&63);return d}function b(a){var d=[],b,e=a.length,l,k,c;for(b=0;b<e;b+=1)l=a[b],128>l?d.push(l):(b+=1,k=a[b],224>l?d.push((l&31)<<6|k&63):(b+=1,c=a[b],d.push((l&15)<<12|(k&63)<<6|c&63)));return d}function p(a){return h(f(a))}
function a(a){return String.fromCharCode.apply(String,c(a))}function n(a){return b(f(a))}function e(a){a=b(a);for(var d="",e=0;e<a.length;)d+=String.fromCharCode.apply(String,a.slice(e,e+45E3)),e+=45E3;return d}function d(a,d,b){var e="",l,k,c;for(c=d;c<b;c+=1)d=a.charCodeAt(c)&255,128>d?e+=String.fromCharCode(d):(c+=1,l=a.charCodeAt(c)&255,224>d?e+=String.fromCharCode((d&31)<<6|l&63):(c+=1,k=a.charCodeAt(c)&255,e+=String.fromCharCode((d&15)<<12|(l&63)<<6|k&63)));return e}function t(a,b){function e(){var m=
c+l;m>a.length&&(m=a.length);k+=d(a,c,m);c=m;m=c===a.length;b(k,m)&&!m&&runtime.setTimeout(e,0)}var l=1E5,k="",c=0;a.length<l?b(d(a,0,a.length),!0):("string"!==typeof a&&(a=a.slice()),e())}function l(a){return g(f(a))}function r(a){return String.fromCharCode.apply(String,g(a))}function k(a){return String.fromCharCode.apply(String,g(f(a)))}var m="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",q=function(a){var d={},b,e;b=0;for(e=a.length;b<e;b+=1)d[a.charAt(b)]=b;return d}(m),w,
u,C=runtime.getWindow(),x,s;C&&C.btoa?(x=function(a){return C.btoa(a)},w=function(a){return x(k(a))}):(x=p,w=function(a){return h(l(a))});C&&C.atob?(s=function(a){return C.atob(a)},u=function(a){a=s(a);return d(a,0,a.length)}):(s=a,u=function(a){return e(c(a))});return function(){this.convertByteArrayToBase64=this.convertUTF8ArrayToBase64=h;this.convertBase64ToByteArray=this.convertBase64ToUTF8Array=c;this.convertUTF16ArrayToByteArray=this.convertUTF16ArrayToUTF8Array=g;this.convertByteArrayToUTF16Array=
this.convertUTF8ArrayToUTF16Array=b;this.convertUTF8StringToBase64=p;this.convertBase64ToUTF8String=a;this.convertUTF8StringToUTF16Array=n;this.convertByteArrayToUTF16String=this.convertUTF8ArrayToUTF16String=e;this.convertUTF8StringToUTF16String=t;this.convertUTF16StringToByteArray=this.convertUTF16StringToUTF8Array=l;this.convertUTF16ArrayToUTF8String=r;this.convertUTF16StringToUTF8String=k;this.convertUTF16StringToBase64=w;this.convertBase64ToUTF16String=u;this.fromBase64=a;this.toBase64=p;this.atob=
s;this.btoa=x;this.utob=k;this.btou=t;this.encode=w;this.encodeURI=function(a){return w(a).replace(/[+\/]/g,function(a){return"+"===a?"-":"_"}).replace(/\\=+$/,"")};this.decode=function(a){return u(a.replace(/[\-_]/g,function(a){return"-"===a?"+":"/"}))}}}();
// Input 3
core.RawDeflate=function(){function f(){this.dl=this.fc=0}function h(){this.extra_bits=this.static_tree=this.dyn_tree=null;this.max_code=this.max_length=this.elems=this.extra_base=0}function c(a,d,b,e){this.good_length=a;this.max_lazy=d;this.nice_length=b;this.max_chain=e}function g(){this.next=null;this.len=0;this.ptr=[];this.ptr.length=b;this.off=0}var b=8192,p,a,n,e,d=null,t,l,r,k,m,q,w,u,C,x,s,v,y,E,D,N,A,O,B,J,L,ea,fa,aa,ba,ga,P,X,U,M,G,H,R,Q,Z,$,ha,na,K,F,ja,oa,W,T,ia,Y,la,da,z,ra,sa,wa=[0,
0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0],pa=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13],I=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,3,7],ua=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15],ta;ta=[new c(0,0,0,0),new c(4,4,8,4),new c(4,5,16,8),new c(4,6,32,32),new c(4,4,16,16),new c(8,16,32,32),new c(8,16,128,128),new c(8,32,128,256),new c(32,128,258,1024),new c(32,258,258,4096)];var ka=function(e){d[l+t++]=e;if(l+t===b){var c;if(0!==t){null!==p?(e=p,p=p.next):e=new g;
e.next=null;e.len=e.off=0;null===a?a=n=e:n=n.next=e;e.len=t-l;for(c=0;c<e.len;c++)e.ptr[c]=d[l+c];t=l=0}}},ma=function(a){a&=65535;l+t<b-2?(d[l+t++]=a&255,d[l+t++]=a>>>8):(ka(a&255),ka(a>>>8))},ca=function(){s=(s<<5^k[A+3-1]&255)&8191;v=w[32768+s];w[A&32767]=v;w[32768+s]=A},V=function(a,d){C>16-d?(u|=a<<C,ma(u),u=a>>16-C,C+=d-16):(u|=a<<C,C+=d)},S=function(a,d){V(d[a].fc,d[a].dl)},va=function(a,d,b){return a[d].fc<a[b].fc||a[d].fc===a[b].fc&&ha[d]<=ha[b]},qa=function(a,d,b){var e;for(e=0;e<b&&sa<
ra.length;e++)a[d+e]=ra.charCodeAt(sa++)&255;return e},za=function(){var a,d,b=65536-J-A;if(-1===b)b--;else if(65274<=A){for(a=0;32768>a;a++)k[a]=k[a+32768];O-=32768;A-=32768;x-=32768;for(a=0;8192>a;a++)d=w[32768+a],w[32768+a]=32768<=d?d-32768:0;for(a=0;32768>a;a++)d=w[a],w[a]=32768<=d?d-32768:0;b+=32768}B||(a=qa(k,A+J,b),0>=a?B=!0:J+=a)},Ca=function(a){var d=L,b=A,e,l=N,c=32506<A?A-32506:0,m=A+258,r=k[b+l-1],s=k[b+l];N>=aa&&(d>>=2);do if(e=a,k[e+l]===s&&k[e+l-1]===r&&k[e]===k[b]&&k[++e]===k[b+1]){b+=
2;e++;do++b;while(k[b]===k[++e]&&k[++b]===k[++e]&&k[++b]===k[++e]&&k[++b]===k[++e]&&k[++b]===k[++e]&&k[++b]===k[++e]&&k[++b]===k[++e]&&k[++b]===k[++e]&&b<m);e=258-(m-b);b=m-258;if(e>l){O=a;l=e;if(258<=e)break;r=k[b+l-1];s=k[b+l]}a=w[a&32767]}while(a>c&&0!==--d);return l},xa=function(a,d){q[W++]=d;0===a?ba[d].fc++:(a--,ba[na[d]+256+1].fc++,ga[(256>a?K[a]:K[256+(a>>7)])&255].fc++,m[T++]=a,Y|=la);la<<=1;0===(W&7)&&(oa[ia++]=Y,Y=0,la=1);if(2<fa&&0===(W&4095)){var b=8*W,e=A-x,l;for(l=0;30>l;l++)b+=ga[l].fc*
(5+pa[l]);b>>=3;if(T<parseInt(W/2,10)&&b<parseInt(e/2,10))return!0}return 8191===W||8192===T},Aa=function(a,d){for(var b=Q[d],e=d<<1;e<=Z;){e<Z&&va(a,Q[e+1],Q[e])&&e++;if(va(a,b,Q[e]))break;Q[d]=Q[e];d=e;e<<=1}Q[d]=b},Da=function(a,d){var b=0;do b|=a&1,a>>=1,b<<=1;while(0<--d);return b>>1},Ea=function(a,d){var b=[];b.length=16;var e=0,l;for(l=1;15>=l;l++)e=e+R[l-1]<<1,b[l]=e;for(e=0;e<=d;e++)l=a[e].dl,0!==l&&(a[e].fc=Da(b[l]++,l))},Ba=function(a){var d=a.dyn_tree,b=a.static_tree,e=a.elems,l,c=-1,
k=e;Z=0;$=573;for(l=0;l<e;l++)0!==d[l].fc?(Q[++Z]=c=l,ha[l]=0):d[l].dl=0;for(;2>Z;)l=Q[++Z]=2>c?++c:0,d[l].fc=1,ha[l]=0,da--,null!==b&&(z-=b[l].dl);a.max_code=c;for(l=Z>>1;1<=l;l--)Aa(d,l);do l=Q[1],Q[1]=Q[Z--],Aa(d,1),b=Q[1],Q[--$]=l,Q[--$]=b,d[k].fc=d[l].fc+d[b].fc,ha[k]=ha[l]>ha[b]+1?ha[l]:ha[b]+1,d[l].dl=d[b].dl=k,Q[1]=k++,Aa(d,1);while(2<=Z);Q[--$]=Q[1];k=a.dyn_tree;l=a.extra_bits;var e=a.extra_base,b=a.max_code,m=a.max_length,r=a.static_tree,s,g,q,f,h=0;for(g=0;15>=g;g++)R[g]=0;k[Q[$]].dl=0;
for(a=$+1;573>a;a++)s=Q[a],g=k[k[s].dl].dl+1,g>m&&(g=m,h++),k[s].dl=g,s>b||(R[g]++,q=0,s>=e&&(q=l[s-e]),f=k[s].fc,da+=f*(g+q),null!==r&&(z+=f*(r[s].dl+q)));if(0!==h){do{for(g=m-1;0===R[g];)g--;R[g]--;R[g+1]+=2;R[m]--;h-=2}while(0<h);for(g=m;0!==g;g--)for(s=R[g];0!==s;)l=Q[--a],l>b||(k[l].dl!==g&&(da+=(g-k[l].dl)*k[l].fc,k[l].fc=g),s--)}Ea(d,c)},Fa=function(a,d){var b,e=-1,l,k=a[0].dl,c=0,m=7,s=4;0===k&&(m=138,s=3);a[d+1].dl=65535;for(b=0;b<=d;b++)l=k,k=a[b+1].dl,++c<m&&l===k||(c<s?U[l].fc+=c:0!==
l?(l!==e&&U[l].fc++,U[16].fc++):10>=c?U[17].fc++:U[18].fc++,c=0,e=l,0===k?(m=138,s=3):l===k?(m=6,s=3):(m=7,s=4))},Ga=function(){8<C?ma(u):0<C&&ka(u);C=u=0},Ha=function(a,d){var b,e=0,l=0,k=0,c=0,s,g;if(0!==W){do 0===(e&7)&&(c=oa[k++]),b=q[e++]&255,0===(c&1)?S(b,a):(s=na[b],S(s+256+1,a),g=wa[s],0!==g&&(b-=F[s],V(b,g)),b=m[l++],s=(256>b?K[b]:K[256+(b>>7)])&255,S(s,d),g=pa[s],0!==g&&(b-=ja[s],V(b,g))),c>>=1;while(e<W)}S(256,a)},Ia=function(a,d){var b,e=-1,l,c=a[0].dl,k=0,m=7,s=4;0===c&&(m=138,s=3);for(b=
0;b<=d;b++)if(l=c,c=a[b+1].dl,!(++k<m&&l===c)){if(k<s){do S(l,U);while(0!==--k)}else 0!==l?(l!==e&&(S(l,U),k--),S(16,U),V(k-3,2)):10>=k?(S(17,U),V(k-3,3)):(S(18,U),V(k-11,7));k=0;e=l;0===c?(m=138,s=3):l===c?(m=6,s=3):(m=7,s=4)}},Ja=function(){var a;for(a=0;286>a;a++)ba[a].fc=0;for(a=0;30>a;a++)ga[a].fc=0;for(a=0;19>a;a++)U[a].fc=0;ba[256].fc=1;Y=W=T=ia=da=z=0;la=1},ya=function(a){var d,b,e,l;l=A-x;oa[ia]=Y;Ba(M);Ba(G);Fa(ba,M.max_code);Fa(ga,G.max_code);Ba(H);for(e=18;3<=e&&0===U[ua[e]].dl;e--);da+=
3*(e+1)+14;d=da+3+7>>3;b=z+3+7>>3;b<=d&&(d=b);if(l+4<=d&&0<=x)for(V(0+a,3),Ga(),ma(l),ma(~l),e=0;e<l;e++)ka(k[x+e]);else if(b===d)V(2+a,3),Ha(P,X);else{V(4+a,3);l=M.max_code+1;d=G.max_code+1;e+=1;V(l-257,5);V(d-1,5);V(e-4,4);for(b=0;b<e;b++)V(U[ua[b]].dl,3);Ia(ba,l-1);Ia(ga,d-1);Ha(ba,ga)}Ja();0!==a&&Ga()},Ka=function(b,e,k){var c,m,s;for(c=0;null!==a&&c<k;){m=k-c;m>a.len&&(m=a.len);for(s=0;s<m;s++)b[e+c+s]=a.ptr[a.off+s];a.off+=m;a.len-=m;c+=m;0===a.len&&(m=a,a=a.next,m.next=p,p=m)}if(c===k)return c;
if(l<t){m=k-c;m>t-l&&(m=t-l);for(s=0;s<m;s++)b[e+c+s]=d[l+s];l+=m;c+=m;t===l&&(t=l=0)}return c},La=function(d,b,c){var m;if(!e){if(!B){C=u=0;var g,q;if(0===X[0].dl){M.dyn_tree=ba;M.static_tree=P;M.extra_bits=wa;M.extra_base=257;M.elems=286;M.max_length=15;M.max_code=0;G.dyn_tree=ga;G.static_tree=X;G.extra_bits=pa;G.extra_base=0;G.elems=30;G.max_length=15;G.max_code=0;H.dyn_tree=U;H.static_tree=null;H.extra_bits=I;H.extra_base=0;H.elems=19;H.max_length=7;for(q=g=H.max_code=0;28>q;q++)for(F[q]=g,m=
0;m<1<<wa[q];m++)na[g++]=q;na[g-1]=q;for(q=g=0;16>q;q++)for(ja[q]=g,m=0;m<1<<pa[q];m++)K[g++]=q;for(g>>=7;30>q;q++)for(ja[q]=g<<7,m=0;m<1<<pa[q]-7;m++)K[256+g++]=q;for(m=0;15>=m;m++)R[m]=0;for(m=0;143>=m;)P[m++].dl=8,R[8]++;for(;255>=m;)P[m++].dl=9,R[9]++;for(;279>=m;)P[m++].dl=7,R[7]++;for(;287>=m;)P[m++].dl=8,R[8]++;Ea(P,287);for(m=0;30>m;m++)X[m].dl=5,X[m].fc=Da(m,5);Ja()}for(m=0;8192>m;m++)w[32768+m]=0;ea=ta[fa].max_lazy;aa=ta[fa].good_length;L=ta[fa].max_chain;x=A=0;J=qa(k,0,65536);if(0>=J)B=
!0,J=0;else{for(B=!1;262>J&&!B;)za();for(m=s=0;2>m;m++)s=(s<<5^k[m]&255)&8191}a=null;l=t=0;3>=fa?(N=2,D=0):(D=2,E=0);r=!1}e=!0;if(0===J)return r=!0,0}m=Ka(d,b,c);if(m===c)return c;if(r)return m;if(3>=fa)for(;0!==J&&null===a;){ca();0!==v&&32506>=A-v&&(D=Ca(v),D>J&&(D=J));if(3<=D)if(q=xa(A-O,D-3),J-=D,D<=ea){D--;do A++,ca();while(0!==--D);A++}else A+=D,D=0,s=k[A]&255,s=(s<<5^k[A+1]&255)&8191;else q=xa(0,k[A]&255),J--,A++;q&&(ya(0),x=A);for(;262>J&&!B;)za()}else for(;0!==J&&null===a;){ca();N=D;y=O;D=
2;0!==v&&(N<ea&&32506>=A-v)&&(D=Ca(v),D>J&&(D=J),3===D&&4096<A-O&&D--);if(3<=N&&D<=N){q=xa(A-1-y,N-3);J-=N-1;N-=2;do A++,ca();while(0!==--N);E=0;D=2;A++;q&&(ya(0),x=A)}else 0!==E?xa(0,k[A-1]&255)&&(ya(0),x=A):E=1,A++,J--;for(;262>J&&!B;)za()}0===J&&(0!==E&&xa(0,k[A-1]&255),ya(1),r=!0);return m+Ka(d,m+b,c-m)};this.deflate=function(l,c){var s,g;ra=l;sa=0;"undefined"===String(typeof c)&&(c=6);(s=c)?1>s?s=1:9<s&&(s=9):s=6;fa=s;B=e=!1;if(null===d){p=a=n=null;d=[];d.length=b;k=[];k.length=65536;m=[];m.length=
8192;q=[];q.length=32832;w=[];w.length=65536;ba=[];ba.length=573;for(s=0;573>s;s++)ba[s]=new f;ga=[];ga.length=61;for(s=0;61>s;s++)ga[s]=new f;P=[];P.length=288;for(s=0;288>s;s++)P[s]=new f;X=[];X.length=30;for(s=0;30>s;s++)X[s]=new f;U=[];U.length=39;for(s=0;39>s;s++)U[s]=new f;M=new h;G=new h;H=new h;R=[];R.length=16;Q=[];Q.length=573;ha=[];ha.length=573;na=[];na.length=256;K=[];K.length=512;F=[];F.length=29;ja=[];ja.length=30;oa=[];oa.length=1024}var r=Array(1024),u=[],v=[];for(s=La(r,0,r.length);0<
s;){v.length=s;for(g=0;g<s;g++)v[g]=String.fromCharCode(r[g]);u[u.length]=v.join("");s=La(r,0,r.length)}ra=null;return u.join("")}};
// Input 4
core.ByteArray=function(f){this.pos=0;this.data=f;this.readUInt32LE=function(){this.pos+=4;var f=this.data,c=this.pos;return f[--c]<<24|f[--c]<<16|f[--c]<<8|f[--c]};this.readUInt16LE=function(){this.pos+=2;var f=this.data,c=this.pos;return f[--c]<<8|f[--c]}};
// Input 5
core.ByteArrayWriter=function(f){var h=this,c=new runtime.ByteArray(0);this.appendByteArrayWriter=function(g){c=runtime.concatByteArrays(c,g.getByteArray())};this.appendByteArray=function(g){c=runtime.concatByteArrays(c,g)};this.appendArray=function(g){c=runtime.concatByteArrays(c,runtime.byteArrayFromArray(g))};this.appendUInt16LE=function(c){h.appendArray([c&255,c>>8&255])};this.appendUInt32LE=function(c){h.appendArray([c&255,c>>8&255,c>>16&255,c>>24&255])};this.appendString=function(g){c=runtime.concatByteArrays(c,
runtime.byteArrayFromString(g,f))};this.getLength=function(){return c.length};this.getByteArray=function(){return c}};
// Input 6
core.RawInflate=function(){var f,h,c=null,g,b,p,a,n,e,d,t,l,r,k,m,q,w,u=[0,1,3,7,15,31,63,127,255,511,1023,2047,4095,8191,16383,32767,65535],C=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258,0,0],x=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0,99,99],s=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577],v=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13],y=[16,17,18,
0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15],E=function(){this.list=this.next=null},D=function(){this.n=this.b=this.e=0;this.t=null},N=function(a,d,b,e,l,c){this.BMAX=16;this.N_MAX=288;this.status=0;this.root=null;this.m=0;var k=Array(this.BMAX+1),m,s,g,q,r,f,u,h=Array(this.BMAX+1),n,p,v,w=new D,t=Array(this.BMAX);q=Array(this.N_MAX);var x,C=Array(this.BMAX+1),A,B,y;y=this.root=null;for(r=0;r<k.length;r++)k[r]=0;for(r=0;r<h.length;r++)h[r]=0;for(r=0;r<t.length;r++)t[r]=null;for(r=0;r<q.length;r++)q[r]=
0;for(r=0;r<C.length;r++)C[r]=0;m=256<d?a[256]:this.BMAX;n=a;p=0;r=d;do k[n[p]]++,p++;while(0<--r);if(k[0]==d)this.root=null,this.status=this.m=0;else{for(f=1;f<=this.BMAX&&0==k[f];f++);u=f;c<f&&(c=f);for(r=this.BMAX;0!=r&&0==k[r];r--);g=r;c>r&&(c=r);for(A=1<<f;f<r;f++,A<<=1)if(0>(A-=k[f])){this.status=2;this.m=c;return}if(0>(A-=k[r]))this.status=2,this.m=c;else{k[r]+=A;C[1]=f=0;n=k;p=1;for(v=2;0<--r;)C[v++]=f+=n[p++];n=a;r=p=0;do 0!=(f=n[p++])&&(q[C[f]++]=r);while(++r<d);d=C[g];C[0]=r=0;n=q;p=0;
q=-1;x=h[0]=0;v=null;for(B=0;u<=g;u++)for(a=k[u];0<a--;){for(;u>x+h[1+q];){x+=h[1+q];q++;B=(B=g-x)>c?c:B;if((s=1<<(f=u-x))>a+1)for(s-=a+1,v=u;++f<B&&!((s<<=1)<=k[++v]);)s-=k[v];x+f>m&&x<m&&(f=m-x);B=1<<f;h[1+q]=f;v=Array(B);for(s=0;s<B;s++)v[s]=new D;y=null==y?this.root=new E:y.next=new E;y.next=null;y.list=v;t[q]=v;0<q&&(C[q]=r,w.b=h[q],w.e=16+f,w.t=v,f=(r&(1<<x)-1)>>x-h[q],t[q-1][f].e=w.e,t[q-1][f].b=w.b,t[q-1][f].n=w.n,t[q-1][f].t=w.t)}w.b=u-x;p>=d?w.e=99:n[p]<b?(w.e=256>n[p]?16:15,w.n=n[p++]):
(w.e=l[n[p]-b],w.n=e[n[p++]-b]);s=1<<u-x;for(f=r>>x;f<B;f+=s)v[f].e=w.e,v[f].b=w.b,v[f].n=w.n,v[f].t=w.t;for(f=1<<u-1;0!=(r&f);f>>=1)r^=f;for(r^=f;(r&(1<<x)-1)!=C[q];)x-=h[q],q--}this.m=h[1];this.status=0!=A&&1!=g?1:0}}},A=function(d){for(;a<d;){var b=p,e;e=q.length==w?-1:q[w++];p=b|e<<a;a+=8}},O=function(a){return p&u[a]},B=function(d){p>>=d;a-=d},J=function(a,b,e){var c,s,q;if(0==e)return 0;for(q=0;;){A(k);s=l.list[O(k)];for(c=s.e;16<c;){if(99==c)return-1;B(s.b);c-=16;A(c);s=s.t[O(c)];c=s.e}B(s.b);
if(16==c)h&=32767,a[b+q++]=f[h++]=s.n;else{if(15==c)break;A(c);d=s.n+O(c);B(c);A(m);s=r.list[O(m)];for(c=s.e;16<c;){if(99==c)return-1;B(s.b);c-=16;A(c);s=s.t[O(c)];c=s.e}B(s.b);A(c);t=h-s.n-O(c);for(B(c);0<d&&q<e;)d--,t&=32767,h&=32767,a[b+q++]=f[h++]=f[t++]}if(q==e)return e}n=-1;return q},L,ea=function(a,d,b){var e,c,q,g,f,u,h,n=Array(316);for(e=0;e<n.length;e++)n[e]=0;A(5);u=257+O(5);B(5);A(5);h=1+O(5);B(5);A(4);e=4+O(4);B(4);if(286<u||30<h)return-1;for(c=0;c<e;c++)A(3),n[y[c]]=O(3),B(3);for(;19>
c;c++)n[y[c]]=0;k=7;c=new N(n,19,19,null,null,k);if(0!=c.status)return-1;l=c.root;k=c.m;g=u+h;for(e=q=0;e<g;)if(A(k),f=l.list[O(k)],c=f.b,B(c),c=f.n,16>c)n[e++]=q=c;else if(16==c){A(2);c=3+O(2);B(2);if(e+c>g)return-1;for(;0<c--;)n[e++]=q}else{17==c?(A(3),c=3+O(3),B(3)):(A(7),c=11+O(7),B(7));if(e+c>g)return-1;for(;0<c--;)n[e++]=0;q=0}k=9;c=new N(n,u,257,C,x,k);0==k&&(c.status=1);if(0!=c.status)return-1;l=c.root;k=c.m;for(e=0;e<h;e++)n[e]=n[e+u];m=6;c=new N(n,h,0,s,v,m);r=c.root;m=c.m;return 0==m&&
257<u||0!=c.status?-1:J(a,d,b)};this.inflate=function(u,y){null==f&&(f=Array(65536));a=p=h=0;n=-1;e=!1;d=t=0;l=null;q=u;w=0;var E=new runtime.ByteArray(y);a:{var D,P;for(D=0;D<y&&(!e||-1!=n);){if(0<d){if(0!=n)for(;0<d&&D<y;)d--,t&=32767,h&=32767,E[0+D++]=f[h++]=f[t++];else{for(;0<d&&D<y;)d--,h&=32767,A(8),E[0+D++]=f[h++]=O(8),B(8);0==d&&(n=-1)}if(D==y)break}if(-1==n){if(e)break;A(1);0!=O(1)&&(e=!0);B(1);A(2);n=O(2);B(2);l=null;d=0}switch(n){case 0:P=E;var X=0+D,U=y-D,M=void 0,M=a&7;B(M);A(16);M=O(16);
B(16);A(16);if(M!=(~p&65535))P=-1;else{B(16);d=M;for(M=0;0<d&&M<U;)d--,h&=32767,A(8),P[X+M++]=f[h++]=O(8),B(8);0==d&&(n=-1);P=M}break;case 1:if(null!=l)P=J(E,0+D,y-D);else b:{P=E;X=0+D;U=y-D;if(null==c){for(var G=void 0,M=Array(288),G=void 0,G=0;144>G;G++)M[G]=8;for(;256>G;G++)M[G]=9;for(;280>G;G++)M[G]=7;for(;288>G;G++)M[G]=8;b=7;G=new N(M,288,257,C,x,b);if(0!=G.status){alert("HufBuild error: "+G.status);P=-1;break b}c=G.root;b=G.m;for(G=0;30>G;G++)M[G]=5;L=5;G=new N(M,30,0,s,v,L);if(1<G.status){c=
null;alert("HufBuild error: "+G.status);P=-1;break b}g=G.root;L=G.m}l=c;r=g;k=b;m=L;P=J(P,X,U)}break;case 2:P=null!=l?J(E,0+D,y-D):ea(E,0+D,y-D);break;default:P=-1}if(-1==P)break a;D+=P}}q=null;return E}};
// Input 7
/*

 Copyright (C) 2012 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
core.LoopWatchDog=function(f,h){var c=Date.now(),g=0;this.check=function(){var b;if(f&&(b=Date.now(),b-c>f))throw runtime.log("alert","watchdog timeout"),"timeout!";if(0<h&&(g+=1,g>h))throw runtime.log("alert","watchdog loop overflow"),"loop overflow";}};
// Input 8
core.Utils=function(){this.hashString=function(f){var h=0,c,g;c=0;for(g=f.length;c<g;c+=1)h=(h<<5)-h+f.charCodeAt(c),h|=0;return h}};
// Input 9
core.DomUtils=function(){function f(c,g){if(c.nodeType===Node.TEXT_NODE)if(0===c.length)c.parentNode.removeChild(c);else if(g.nodeType===Node.TEXT_NODE)return g.insertData(0,c.data),c.parentNode.removeChild(c),g;return c}function h(c,g){return c===g||Boolean(c.compareDocumentPosition(g)&Node.DOCUMENT_POSITION_CONTAINED_BY)}this.splitBoundaries=function(c){var g=[],b;if(c.startContainer.nodeType===Node.TEXT_NODE||c.endContainer.nodeType===Node.TEXT_NODE){b=c.endContainer;var f=c.endOffset;if(f<b.childNodes.length)for(b=
b.childNodes[f],f=0;b.firstChild;)b=b.firstChild;else for(;b.lastChild;)b=b.lastChild,f=b.nodeType===Node.TEXT_NODE?b.textContent.length:b.childNodes.length;c.setEnd(b,f);0!==c.endOffset&&(c.endContainer.nodeType===Node.TEXT_NODE&&c.endOffset!==c.endContainer.length)&&(g.push(c.endContainer.splitText(c.endOffset)),g.push(c.endContainer));0!==c.startOffset&&(c.startContainer.nodeType===Node.TEXT_NODE&&c.startOffset!==c.startContainer.length)&&(b=c.startContainer.splitText(c.startOffset),g.push(c.startContainer),
g.push(b),c.setStart(b,0))}return g};this.containsRange=function(c,f){return 0>=c.compareBoundaryPoints(c.START_TO_START,f)&&0<=c.compareBoundaryPoints(c.END_TO_END,f)};this.rangesIntersect=function(c,f){return 0>=c.compareBoundaryPoints(c.END_TO_START,f)&&0<=c.compareBoundaryPoints(c.START_TO_END,f)};this.getNodesInRange=function(c,f){var b=[],h,a=c.startContainer.ownerDocument.createTreeWalker(c.commonAncestorContainer,NodeFilter.SHOW_ALL,f,!1);for(h=a.currentNode=c.startContainer;h;){if(f(h)===
NodeFilter.FILTER_ACCEPT)b.push(h);else if(f(h)===NodeFilter.FILTER_REJECT)break;h=h.parentNode}b.reverse();for(h=a.nextNode();h;)b.push(h),h=a.nextNode();return b};this.normalizeTextNodes=function(c){c&&c.nextSibling&&(c=f(c,c.nextSibling));c&&c.previousSibling&&f(c.previousSibling,c)};this.rangeContainsNode=function(c,f){var b=f.ownerDocument.createRange(),h=f.nodeType===Node.TEXT_NODE?f.length:f.childNodes.length;b.setStart(c.startContainer,c.startOffset);b.setEnd(c.endContainer,c.endOffset);h=
0===b.comparePoint(f,0)&&0===b.comparePoint(f,h);b.detach();return h};this.mergeIntoParent=function(c){for(var f=c.parentNode;c.firstChild;)f.insertBefore(c.firstChild,c);f.removeChild(c);return f};this.getElementsByTagNameNS=function(c,f,b){return Array.prototype.slice.call(c.getElementsByTagNameNS(f,b))};this.rangeIntersectsNode=function(c,f){var b=f.nodeType===Node.TEXT_NODE?f.length:f.childNodes.length;return 0>=c.comparePoint(f,0)&&0<=c.comparePoint(f,b)};this.containsNode=function(c,f){return c===
f||c.contains(f)};(function(c){var f=runtime.getWindow();null!==f&&(f=f.navigator.appVersion.toLowerCase(),f=-1===f.indexOf("chrome")&&(-1!==f.indexOf("applewebkit")||-1!==f.indexOf("safari")))&&(c.containsNode=h)})(this)};
// Input 10
runtime.loadClass("core.DomUtils");
core.Cursor=function(f,h){function c(a){a.parentNode&&(n.push(a.previousSibling),n.push(a.nextSibling),a.parentNode.removeChild(a))}function g(a,d,b){if(d.nodeType===Node.TEXT_NODE){runtime.assert(Boolean(d),"putCursorIntoTextNode: invalid container");var e=d.parentNode;runtime.assert(Boolean(e),"putCursorIntoTextNode: container without parent");runtime.assert(0<=b&&b<=d.length,"putCursorIntoTextNode: offset is out of bounds");0===b?e.insertBefore(a,d):(b!==d.length&&d.splitText(b),e.insertBefore(a,
d.nextSibling))}else if(d.nodeType===Node.ELEMENT_NODE){runtime.assert(Boolean(d),"putCursorIntoContainer: invalid container");for(e=d.firstChild;null!==e&&0<b;)e=e.nextSibling,b-=1;d.insertBefore(a,e)}n.push(a.previousSibling);n.push(a.nextSibling)}var b=f.createElementNS("urn:webodf:names:cursor","cursor"),p=f.createElementNS("urn:webodf:names:cursor","anchor"),a,n=[],e,d,t=new core.DomUtils;this.getNode=function(){return b};this.getAnchorNode=function(){return p.parentNode?p:b};this.getSelectedRange=
function(){d?(e.setStartBefore(b),e.collapse(!0)):(e.setStartAfter(a?p:b),e.setEndBefore(a?b:p));return e};this.setSelectedRange=function(l,f){e&&e!==l&&e.detach();e=l;a=!1!==f;(d=l.collapsed)?(c(p),c(b),g(b,l.startContainer,l.startOffset)):(c(p),c(b),g(a?b:p,l.endContainer,l.endOffset),g(a?p:b,l.startContainer,l.startOffset));n.forEach(t.normalizeTextNodes);n.length=0};this.remove=function(){c(b);n.forEach(t.normalizeTextNodes);n.length=0};b.setAttributeNS("urn:webodf:names:cursor","memberId",h);
p.setAttributeNS("urn:webodf:names:cursor","memberId",h)};
// Input 11
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
core.EventNotifier=function(f){var h={};this.emit=function(c,f){var b,p;runtime.assert(h.hasOwnProperty(c),'unknown event fired "'+c+'"');p=h[c];for(b=0;b<p.length;b+=1)p[b](f)};this.subscribe=function(c,f){runtime.assert(h.hasOwnProperty(c),'tried to subscribe to unknown event "'+c+'"');h[c].push(f);runtime.log('event "'+c+'" subscribed.')};this.unsubscribe=function(c,f){var b;runtime.assert(h.hasOwnProperty(c),'tried to unsubscribe from unknown event "'+c+'"');b=h[c].indexOf(f);runtime.assert(-1!==
b,'tried to unsubscribe unknown callback from event "'+c+'"');-1!==b&&h[c].splice(b,1);runtime.log('event "'+c+'" unsubscribed.')};(function(){var c;for(c=0;c<f.length;c+=1)h[f[c]]=[]})()};
// Input 12
core.UnitTest=function(){};core.UnitTest.prototype.setUp=function(){};core.UnitTest.prototype.tearDown=function(){};core.UnitTest.prototype.description=function(){};core.UnitTest.prototype.tests=function(){};core.UnitTest.prototype.asyncTests=function(){};
core.UnitTest.provideTestAreaDiv=function(){var f=runtime.getWindow().document,h=f.getElementById("testarea");runtime.assert(!h,'Unclean test environment, found a div with id "testarea".');h=f.createElement("div");h.setAttribute("id","testarea");f.body.appendChild(h);return h};
core.UnitTest.cleanupTestAreaDiv=function(){var f=runtime.getWindow().document,h=f.getElementById("testarea");runtime.assert(!!h&&h.parentNode===f.body,'Test environment broken, found no div with id "testarea" below body.');f.body.removeChild(h)};
core.UnitTestRunner=function(){function f(b){a+=1;runtime.log("fail",b)}function h(a,d){var b;try{if(a.length!==d.length)return f("array of length "+a.length+" should be "+d.length+" long"),!1;for(b=0;b<a.length;b+=1)if(a[b]!==d[b])return f(a[b]+" should be "+d[b]+" at array index "+b),!1}catch(c){return!1}return!0}function c(a,d,b){var l=a.attributes,r=l.length,k,m,q;for(k=0;k<r;k+=1)if(m=l.item(k),"xmlns"!==m.prefix){q=d.getAttributeNS(m.namespaceURI,m.localName);if(!d.hasAttributeNS(m.namespaceURI,
m.localName))return f("Attribute "+m.localName+" with value "+m.value+" was not present"),!1;if(q!==m.value)return f("Attribute "+m.localName+" was "+q+" should be "+m.value),!1}return b?!0:c(d,a,!0)}function g(a,d){if(a.nodeType!==d.nodeType)return f(a.nodeType+" should be "+d.nodeType),!1;if(a.nodeType===Node.TEXT_NODE)return a.data===d.data;runtime.assert(a.nodeType===Node.ELEMENT_NODE,"Only textnodes and elements supported.");if(a.namespaceURI!==d.namespaceURI||a.localName!==d.localName)return f(a.namespaceURI+
" should be "+d.namespaceURI),!1;if(!c(a,d,!1))return!1;for(var b=a.firstChild,l=d.firstChild;b;){if(!l||!g(b,l))return!1;b=b.nextSibling;l=l.nextSibling}return l?!1:!0}function b(a,d){return 0===d?a===d&&1/a===1/d:a===d?!0:"number"===typeof d&&isNaN(d)?"number"===typeof a&&isNaN(a):Object.prototype.toString.call(d)===Object.prototype.toString.call([])?h(a,d):"object"===typeof d&&"object"===typeof a?d.constructor===Element||d.constructor===Node?g(d,a):n(d,a):!1}function p(a,d,c){"string"===typeof d&&
"string"===typeof c||runtime.log("WARN: shouldBe() expects string arguments");var l,r;try{r=eval(d)}catch(k){l=k}a=eval(c);l?f(d+" should be "+a+". Threw exception "+l):b(r,a)?runtime.log("pass",d+" is "+c):String(typeof r)===String(typeof a)?(c=0===r&&0>1/r?"-0":String(r),f(d+" should be "+a+". Was "+c+".")):f(d+" should be "+a+" (of type "+typeof a+"). Was "+r+" (of type "+typeof r+").")}var a=0,n;n=function(a,d){var c=Object.keys(a),l=Object.keys(d);c.sort();l.sort();return h(c,l)&&Object.keys(a).every(function(c){var l=
a[c],m=d[c];return b(l,m)?!0:(f(l+" should be "+m+" for key "+c),!1)})};this.areNodesEqual=g;this.shouldBeNull=function(a,d){p(a,d,"null")};this.shouldBeNonNull=function(a,d){var b,c;try{c=eval(d)}catch(r){b=r}b?f(d+" should be non-null. Threw exception "+b):null!==c?runtime.log("pass",d+" is non-null."):f(d+" should be non-null. Was "+c)};this.shouldBe=p;this.countFailedTests=function(){return a}};
core.UnitTester=function(){function f(c,b){return"<span style='color:blue;cursor:pointer' onclick='"+b+"'>"+c+"</span>"}var h=0,c={};this.runTests=function(g,b,p){function a(l){if(0===l.length)c[n]=t,h+=e.countFailedTests(),b();else{r=l[0];var k=Runtime.getFunctionName(r);runtime.log("Running "+k);m=e.countFailedTests();d.setUp();r(function(){d.tearDown();t[k]=m===e.countFailedTests();a(l.slice(1))})}}var n=Runtime.getFunctionName(g),e=new core.UnitTestRunner,d=new g(e),t={},l,r,k,m,q="BrowserRuntime"===
runtime.type();if(c.hasOwnProperty(n))runtime.log("Test "+n+" has already run.");else{q?runtime.log("<span>Running "+f(n,'runSuite("'+n+'");')+": "+d.description()+"</span>"):runtime.log("Running "+n+": "+d.description);k=d.tests();for(l=0;l<k.length;l+=1)r=k[l],g=Runtime.getFunctionName(r)||r.testName,p.length&&-1===p.indexOf(g)||(q?runtime.log("<span>Running "+f(g,'runTest("'+n+'","'+g+'")')+"</span>"):runtime.log("Running "+g),m=e.countFailedTests(),d.setUp(),r(),d.tearDown(),t[g]=m===e.countFailedTests());
a(d.asyncTests())}};this.countFailedTests=function(){return h};this.results=function(){return c}};
// Input 13
core.PositionIterator=function(f,h,c,g){function b(){this.acceptNode=function(a){return a.nodeType===Node.TEXT_NODE&&0===a.length?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}}function p(a){this.acceptNode=function(b){return b.nodeType===Node.TEXT_NODE&&0===b.length?NodeFilter.FILTER_REJECT:a.acceptNode(b)}}function a(){var a=e.currentNode.nodeType;d=a===Node.TEXT_NODE?e.currentNode.length-1:a===Node.ELEMENT_NODE?1:0}var n=this,e,d,t;this.nextPosition=function(){if(e.currentNode===f)return!1;
if(0===d&&e.currentNode.nodeType===Node.ELEMENT_NODE)null===e.firstChild()&&(d=1);else if(e.currentNode.nodeType===Node.TEXT_NODE&&d+1<e.currentNode.length)d+=1;else if(null!==e.nextSibling())d=0;else if(e.parentNode())d=1;else return!1;return!0};this.previousPosition=function(){var b=!0;if(0===d)if(null===e.previousSibling()){if(!e.parentNode()||e.currentNode===f)return e.firstChild(),!1;d=0}else a();else e.currentNode.nodeType===Node.TEXT_NODE?d-=1:null!==e.lastChild()?a():e.currentNode===f?b=!1:
d=0;return b};this.container=function(){var a=e.currentNode,b=a.nodeType;return 0===d&&b!==Node.TEXT_NODE?a.parentNode:a};this.rightNode=function(){var a=e.currentNode,b=a.nodeType;if(b===Node.TEXT_NODE&&d===a.length)for(a=a.nextSibling;a&&1!==t(a);)a=a.nextSibling;else b===Node.ELEMENT_NODE&&1===d&&(a=null);return a};this.leftNode=function(){var a=e.currentNode;if(0===d)for(a=a.previousSibling;a&&1!==t(a);)a=a.previousSibling;else if(a.nodeType===Node.ELEMENT_NODE)for(a=a.lastChild;a&&1!==t(a);)a=
a.previousSibling;return a};this.getCurrentNode=function(){return e.currentNode};this.domOffset=function(){if(e.currentNode.nodeType===Node.TEXT_NODE)return d;var a=0,b=e.currentNode,c;for(c=1===d?e.lastChild():e.previousSibling();c;)a+=1,c=e.previousSibling();e.currentNode=b;return a};this.unfilteredDomOffset=function(){if(e.currentNode.nodeType===Node.TEXT_NODE)return d;for(var a=0,b=e.currentNode,b=1===d?b.lastChild:b.previousSibling;b;)a+=1,b=b.previousSibling;return a};this.getPreviousSibling=
function(){var a=e.currentNode,b=e.previousSibling();e.currentNode=a;return b};this.getNextSibling=function(){var a=e.currentNode,b=e.nextSibling();e.currentNode=a;return b};this.setUnfilteredPosition=function(a,b){var c;runtime.assert(null!==a&&void 0!==a,"PositionIterator.setUnfilteredPosition called without container");e.currentNode=a;if(a.nodeType===Node.TEXT_NODE)return d=b,runtime.assert(b<=a.length,"Error in setPosition: "+b+" > "+a.length),runtime.assert(0<=b,"Error in setPosition: "+b+" < 0"),
b===a.length&&(d=void 0,e.nextSibling()?d=0:e.parentNode()&&(d=1),runtime.assert(void 0!==d,"Error in setPosition: position not valid.")),!0;c=t(a);b<a.childNodes.length&&c!==NodeFilter.FILTER_REJECT?(e.currentNode=a.childNodes[b],c=t(e.currentNode),d=0):d=0===b?0:1;c===NodeFilter.FILTER_REJECT&&(d=1);if(c!==NodeFilter.FILTER_ACCEPT)return n.nextPosition();runtime.assert(t(e.currentNode)===NodeFilter.FILTER_ACCEPT,"PositionIterater.setUnfilteredPosition call resulted in an non-visible node being set");
return!0};this.moveToEnd=function(){e.currentNode=f;d=1};this.moveToEndOfNode=function(a){a.nodeType===Node.TEXT_NODE?n.setUnfilteredPosition(a,a.length):(e.currentNode=a,d=1)};this.getNodeFilter=function(){return t};t=(c?new p(c):new b).acceptNode;t.acceptNode=t;e=f.ownerDocument.createTreeWalker(f,h||4294967295,t,g);d=0;null===e.firstChild()&&(d=1)};
// Input 14
runtime.loadClass("core.PositionIterator");core.PositionFilter=function(){};core.PositionFilter.FilterResult={FILTER_ACCEPT:1,FILTER_REJECT:2,FILTER_SKIP:3};core.PositionFilter.prototype.acceptPosition=function(f){};(function(){return core.PositionFilter})();
// Input 15
runtime.loadClass("core.PositionFilter");core.PositionFilterChain=function(){var f={},h=core.PositionFilter.FilterResult.FILTER_ACCEPT,c=core.PositionFilter.FilterResult.FILTER_REJECT;this.acceptPosition=function(g){for(var b in f)if(f.hasOwnProperty(b)&&f[b].acceptPosition(g)===c)return c;return h};this.addFilter=function(c,b){f[c]=b};this.removeFilter=function(c){delete f[c]}};
// Input 16
core.Async=function(){this.forEach=function(f,h,c){function g(b){a!==p&&(b?(a=p,c(b)):(a+=1,a===p&&c(null)))}var b,p=f.length,a=0;for(b=0;b<p;b+=1)h(f[b],g)}};
// Input 17
/*

 WebODF
 Copyright (c) 2010 Jos van den Oever
 Licensed under the ... License:

 Project home: http://www.webodf.org/
*/
runtime.loadClass("core.RawInflate");runtime.loadClass("core.ByteArray");runtime.loadClass("core.ByteArrayWriter");runtime.loadClass("core.Base64");
core.Zip=function(f,h){function c(a){var b=[0,1996959894,3993919788,2567524794,124634137,1886057615,3915621685,2657392035,249268274,2044508324,3772115230,2547177864,162941995,2125561021,3887607047,2428444049,498536548,1789927666,4089016648,2227061214,450548861,1843258603,4107580753,2211677639,325883990,1684777152,4251122042,2321926636,335633487,1661365465,4195302755,2366115317,997073096,1281953886,3579855332,2724688242,1006888145,1258607687,3524101629,2768942443,901097722,1119000684,3686517206,2898065728,
853044451,1172266101,3705015759,2882616665,651767980,1373503546,3369554304,3218104598,565507253,1454621731,3485111705,3099436303,671266974,1594198024,3322730930,2970347812,795835527,1483230225,3244367275,3060149565,1994146192,31158534,2563907772,4023717930,1907459465,112637215,2680153253,3904427059,2013776290,251722036,2517215374,3775830040,2137656763,141376813,2439277719,3865271297,1802195444,476864866,2238001368,4066508878,1812370925,453092731,2181625025,4111451223,1706088902,314042704,2344532202,
4240017532,1658658271,366619977,2362670323,4224994405,1303535960,984961486,2747007092,3569037538,1256170817,1037604311,2765210733,3554079995,1131014506,879679996,2909243462,3663771856,1141124467,855842277,2852801631,3708648649,1342533948,654459306,3188396048,3373015174,1466479909,544179635,3110523913,3462522015,1591671054,702138776,2966460450,3352799412,1504918807,783551873,3082640443,3233442989,3988292384,2596254646,62317068,1957810842,3939845945,2647816111,81470997,1943803523,3814918930,2489596804,
225274430,2053790376,3826175755,2466906013,167816743,2097651377,4027552580,2265490386,503444072,1762050814,4150417245,2154129355,426522225,1852507879,4275313526,2312317920,282753626,1742555852,4189708143,2394877945,397917763,1622183637,3604390888,2714866558,953729732,1340076626,3518719985,2797360999,1068828381,1219638859,3624741850,2936675148,906185462,1090812512,3747672003,2825379669,829329135,1181335161,3412177804,3160834842,628085408,1382605366,3423369109,3138078467,570562233,1426400815,3317316542,
2998733608,733239954,1555261956,3268935591,3050360625,752459403,1541320221,2607071920,3965973030,1969922972,40735498,2617837225,3943577151,1913087877,83908371,2512341634,3803740692,2075208622,213261112,2463272603,3855990285,2094854071,198958881,2262029012,4057260610,1759359992,534414190,2176718541,4139329115,1873836001,414664567,2282248934,4279200368,1711684554,285281116,2405801727,4167216745,1634467795,376229701,2685067896,3608007406,1308918612,956543938,2808555105,3495958263,1231636301,1047427035,
2932959818,3654703836,1088359270,936918E3,2847714899,3736837829,1202900863,817233897,3183342108,3401237130,1404277552,615818150,3134207493,3453421203,1423857449,601450431,3009837614,3294710456,1567103746,711928724,3020668471,3272380065,1510334235,755167117],d,c,e=a.length,k=0,k=0;d=-1;for(c=0;c<e;c+=1)k=(d^a[c])&255,k=b[k],d=d>>>8^k;return d^-1}function g(a){return new Date((a>>25&127)+1980,(a>>21&15)-1,a>>16&31,a>>11&15,a>>5&63,(a&31)<<1)}function b(a){var b=a.getFullYear();return 1980>b?0:b-1980<<
25|a.getMonth()+1<<21|a.getDate()<<16|a.getHours()<<11|a.getMinutes()<<5|a.getSeconds()>>1}function p(a,b){var d,c,e,k,l,f,q,r=this;this.load=function(b){if(void 0!==r.data)b(null,r.data);else{var d=l+34+c+e+256;d+q>m&&(d=m-q);runtime.read(a,q,d,function(d,c){if(d||null===c)b(d,c);else a:{var e=c,m=new core.ByteArray(e),s=m.readUInt32LE(),q;if(67324752!==s)b("File entry signature is wrong."+s.toString()+" "+e.length.toString(),null);else{m.pos+=22;s=m.readUInt16LE();q=m.readUInt16LE();m.pos+=s+q;
if(k){e=e.slice(m.pos,m.pos+l);if(l!==e.length){b("The amount of compressed bytes read was "+e.length.toString()+" instead of "+l.toString()+" for "+r.filename+" in "+a+".",null);break a}e=w(e,f)}else e=e.slice(m.pos,m.pos+f);f!==e.length?b("The amount of bytes read was "+e.length.toString()+" instead of "+f.toString()+" for "+r.filename+" in "+a+".",null):(r.data=e,b(null,e))}}})}};this.set=function(a,b,d,c){r.filename=a;r.data=b;r.compressed=d;r.date=c};this.error=null;b&&(d=b.readUInt32LE(),33639248!==
d?this.error="Central directory entry has wrong signature at position "+(b.pos-4).toString()+' for file "'+a+'": '+b.data.length.toString():(b.pos+=6,k=b.readUInt16LE(),this.date=g(b.readUInt32LE()),b.readUInt32LE(),l=b.readUInt32LE(),f=b.readUInt32LE(),c=b.readUInt16LE(),e=b.readUInt16LE(),d=b.readUInt16LE(),b.pos+=8,q=b.readUInt32LE(),this.filename=runtime.byteArrayToString(b.data.slice(b.pos,b.pos+c),"utf8"),b.pos+=c+e+d))}function a(a,b){if(22!==a.length)b("Central directory length should be 22.",
u);else{var d=new core.ByteArray(a),c;c=d.readUInt32LE();101010256!==c?b("Central directory signature is wrong: "+c.toString(),u):(c=d.readUInt16LE(),0!==c?b("Zip files with non-zero disk numbers are not supported.",u):(c=d.readUInt16LE(),0!==c?b("Zip files with non-zero disk numbers are not supported.",u):(c=d.readUInt16LE(),q=d.readUInt16LE(),c!==q?b("Number of entries is inconsistent.",u):(c=d.readUInt32LE(),d=d.readUInt16LE(),d=m-22-c,runtime.read(f,d,m-d,function(a,d){if(a||null===d)b(a,u);else a:{var c=
new core.ByteArray(d),e,l;k=[];for(e=0;e<q;e+=1){l=new p(f,c);if(l.error){b(l.error,u);break a}k[k.length]=l}b(null,u)}})))))}}function n(a,b){var d=null,c,e;for(e=0;e<k.length;e+=1)if(c=k[e],c.filename===a){d=c;break}d?d.data?b(null,d.data):d.load(b):b(a+" not found.",null)}function e(a){var d=new core.ByteArrayWriter("utf8"),e=0;d.appendArray([80,75,3,4,20,0,0,0,0,0]);a.data&&(e=a.data.length);d.appendUInt32LE(b(a.date));d.appendUInt32LE(c(a.data));d.appendUInt32LE(e);d.appendUInt32LE(e);d.appendUInt16LE(a.filename.length);
d.appendUInt16LE(0);d.appendString(a.filename);a.data&&d.appendByteArray(a.data);return d}function d(a,d){var e=new core.ByteArrayWriter("utf8"),k=0;e.appendArray([80,75,1,2,20,0,20,0,0,0,0,0]);a.data&&(k=a.data.length);e.appendUInt32LE(b(a.date));e.appendUInt32LE(c(a.data));e.appendUInt32LE(k);e.appendUInt32LE(k);e.appendUInt16LE(a.filename.length);e.appendArray([0,0,0,0,0,0,0,0,0,0,0,0]);e.appendUInt32LE(d);e.appendString(a.filename);return e}function t(a,b){if(a===k.length)b(null);else{var d=k[a];
void 0!==d.data?t(a+1,b):d.load(function(d){d?b(d):t(a+1,b)})}}function l(a,b){t(0,function(c){if(c)b(c);else{c=new core.ByteArrayWriter("utf8");var l,m,f,q=[0];for(l=0;l<k.length;l+=1)c.appendByteArrayWriter(e(k[l])),q.push(c.getLength());f=c.getLength();for(l=0;l<k.length;l+=1)m=k[l],c.appendByteArrayWriter(d(m,q[l]));l=c.getLength()-f;c.appendArray([80,75,5,6,0,0,0,0]);c.appendUInt16LE(k.length);c.appendUInt16LE(k.length);c.appendUInt32LE(l);c.appendUInt32LE(f);c.appendArray([0,0]);a(c.getByteArray())}})}
function r(a,b){l(function(d){runtime.writeFile(a,d,b)},b)}var k,m,q,w=(new core.RawInflate).inflate,u=this,C=new core.Base64;this.load=n;this.save=function(a,b,d,c){var e,l;for(e=0;e<k.length;e+=1)if(l=k[e],l.filename===a){l.set(a,b,d,c);return}l=new p(f);l.set(a,b,d,c);k.push(l)};this.write=function(a){r(f,a)};this.writeAs=r;this.createByteArray=l;this.loadContentXmlAsFragments=function(a,b){u.loadAsString(a,function(a,d){if(a)return b.rootElementReady(a);b.rootElementReady(null,d,!0)})};this.loadAsString=
function(a,b){n(a,function(a,d){if(a||null===d)return b(a,null);var c=runtime.byteArrayToString(d,"utf8");b(null,c)})};this.loadAsDOM=function(a,b){u.loadAsString(a,function(a,d){if(a||null===d)b(a,null);else{var c=(new DOMParser).parseFromString(d,"text/xml");b(null,c)}})};this.loadAsDataURL=function(a,b,d){n(a,function(a,c){if(a)return d(a,null);var e=0,l;b||(b=80===c[1]&&78===c[2]&&71===c[3]?"image/png":255===c[0]&&216===c[1]&&255===c[2]?"image/jpeg":71===c[0]&&73===c[1]&&70===c[2]?"image/gif":
"");for(l="data:"+b+";base64,";e<c.length;)l+=C.convertUTF8ArrayToBase64(c.slice(e,Math.min(e+45E3,c.length))),e+=45E3;d(null,l)})};this.getEntries=function(){return k.slice()};m=-1;null===h?k=[]:runtime.getFileSize(f,function(b){m=b;0>m?h("File '"+f+"' cannot be read.",u):runtime.read(f,m-22,22,function(b,d){b||null===h||null===d?h(b,u):a(d,h)})})};
// Input 18
core.CSSUnits=function(){var f={"in":1,cm:2.54,mm:25.4,pt:72,pc:12};this.convert=function(h,c,g){return h*f[g]/f[c]};this.convertMeasure=function(f,c){var g,b;f&&c?(g=parseFloat(f),b=f.replace(g.toString(),""),g=this.convert(g,b,c)):g="";return g.toString()};this.getUnits=function(f){return f.substr(f.length-2,f.length)}};
// Input 19
xmldom.LSSerializerFilter=function(){};
// Input 20
"function"!==typeof Object.create&&(Object.create=function(f){var h=function(){};h.prototype=f;return new h});
xmldom.LSSerializer=function(){function f(b){var c=b||{},a=function(a){var b={},d;for(d in a)a.hasOwnProperty(d)&&(b[a[d]]=d);return b}(b),f=[c],e=[a],d=0;this.push=function(){d+=1;c=f[d]=Object.create(c);a=e[d]=Object.create(a)};this.pop=function(){f[d]=void 0;e[d]=void 0;d-=1;c=f[d];a=e[d]};this.getLocalNamespaceDefinitions=function(){return a};this.getQName=function(b){var d=b.namespaceURI,e=0,k;if(!d)return b.localName;if(k=a[d])return k+":"+b.localName;do{k||!b.prefix?(k="ns"+e,e+=1):k=b.prefix;
if(c[k]===d)break;if(!c[k]){c[k]=d;a[d]=k;break}k=null}while(null===k);return k+":"+b.localName}}function h(b){return b.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/'/g,"&apos;").replace(/"/g,"&quot;")}function c(b,f){var a="",n=g.filter?g.filter.acceptNode(f):NodeFilter.FILTER_ACCEPT,e;if(n===NodeFilter.FILTER_ACCEPT&&f.nodeType===Node.ELEMENT_NODE){b.push();e=b.getQName(f);var d,t=f.attributes,l,r,k,m="",q;d="<"+e;l=t.length;for(r=0;r<l;r+=1)k=t.item(r),"http://www.w3.org/2000/xmlns/"!==
k.namespaceURI&&(q=g.filter?g.filter.acceptNode(k):NodeFilter.FILTER_ACCEPT,q===NodeFilter.FILTER_ACCEPT&&(q=b.getQName(k),k="string"===typeof k.value?h(k.value):k.value,m+=" "+(q+'="'+k+'"')));l=b.getLocalNamespaceDefinitions();for(r in l)l.hasOwnProperty(r)&&((t=l[r])?"xmlns"!==t&&(d+=" xmlns:"+l[r]+'="'+r+'"'):d+=' xmlns="'+r+'"');a+=d+(m+">")}if(n===NodeFilter.FILTER_ACCEPT||n===NodeFilter.FILTER_SKIP){for(n=f.firstChild;n;)a+=c(b,n),n=n.nextSibling;f.nodeValue&&(a+=h(f.nodeValue))}e&&(a+="</"+
e+">",b.pop());return a}var g=this;this.filter=null;this.writeToString=function(b,g){if(!b)return"";var a=new f(g);return c(a,b)}};
// Input 21
xmldom.RelaxNGParser=function(){function f(a,b){this.message=function(){b&&(a+=1===b.nodeType?" Element ":" Node ",a+=b.nodeName,b.nodeValue&&(a+=" with value '"+b.nodeValue+"'"),a+=".");return a}}function h(a){if(2>=a.e.length)return a;var b={name:a.name,e:a.e.slice(0,2)};return h({name:a.name,e:[b].concat(a.e.slice(2))})}function c(a){a=a.split(":",2);var b="",c;1===a.length?a=["",a[0]]:b=a[0];for(c in n)n[c]===b&&(a[0]=c);return a}function g(a,b){for(var e=0,f,k,m=a.name;a.e&&e<a.e.length;)if(f=
a.e[e],"ref"===f.name){k=b[f.a.name];if(!k)throw f.a.name+" was not defined.";f=a.e.slice(e+1);a.e=a.e.slice(0,e);a.e=a.e.concat(k.e);a.e=a.e.concat(f)}else e+=1,g(f,b);f=a.e;"choice"!==m||f&&f[1]&&"empty"!==f[1].name||(f&&f[0]&&"empty"!==f[0].name?(f[1]=f[0],f[0]={name:"empty"}):(delete a.e,a.name="empty"));if("group"===m||"interleave"===m)"empty"===f[0].name?"empty"===f[1].name?(delete a.e,a.name="empty"):(m=a.name=f[1].name,a.names=f[1].names,f=a.e=f[1].e):"empty"===f[1].name&&(m=a.name=f[0].name,
a.names=f[0].names,f=a.e=f[0].e);"oneOrMore"===m&&"empty"===f[0].name&&(delete a.e,a.name="empty");if("attribute"===m){k=a.names?a.names.length:0;for(var q,h=[],u=[],e=0;e<k;e+=1)q=c(a.names[e]),u[e]=q[0],h[e]=q[1];a.localnames=h;a.namespaces=u}"interleave"===m&&("interleave"===f[0].name?a.e="interleave"===f[1].name?f[0].e.concat(f[1].e):[f[1]].concat(f[0].e):"interleave"===f[1].name&&(a.e=[f[0]].concat(f[1].e)))}function b(a,c){for(var e=0,f;a.e&&e<a.e.length;)f=a.e[e],"elementref"===f.name?(f.id=
f.id||0,a.e[e]=c[f.id]):"element"!==f.name&&b(f,c),e+=1}var p=this,a,n={"http://www.w3.org/XML/1998/namespace":"xml"},e;e=function(a,b,f){var g=[],k,m,q=a.localName,w=[];k=a.attributes;var u=q,p=w,x={},s,v;for(s=0;s<k.length;s+=1)if(v=k.item(s),v.namespaceURI)"http://www.w3.org/2000/xmlns/"===v.namespaceURI&&(n[v.value]=v.localName);else{"name"!==v.localName||"element"!==u&&"attribute"!==u||p.push(v.value);if("name"===v.localName||"combine"===v.localName||"type"===v.localName){var y=v,E;E=v.value;
E=E.replace(/^\s\s*/,"");for(var D=/\s/,N=E.length-1;D.test(E.charAt(N));)N-=1;E=E.slice(0,N+1);y.value=E}x[v.localName]=v.value}k=x;k.combine=k.combine||void 0;a=a.firstChild;u=g;p=w;for(x="";a;){if(a.nodeType===Node.ELEMENT_NODE&&"http://relaxng.org/ns/structure/1.0"===a.namespaceURI){if(s=e(a,b,u))"name"===s.name?p.push(n[s.a.ns]+":"+s.text):"choice"===s.name&&(s.names&&s.names.length)&&(p=p.concat(s.names),delete s.names),u.push(s)}else a.nodeType===Node.TEXT_NODE&&(x+=a.nodeValue);a=a.nextSibling}a=
x;"value"!==q&&"param"!==q&&(a=/^\s*([\s\S]*\S)?\s*$/.exec(a)[1]);"value"===q&&void 0===k.type&&(k.type="token",k.datatypeLibrary="");"attribute"!==q&&"element"!==q||void 0===k.name||(m=c(k.name),g=[{name:"name",text:m[1],a:{ns:m[0]}}].concat(g),delete k.name);"name"===q||"nsName"===q||"value"===q?void 0===k.ns&&(k.ns=""):delete k.ns;"name"===q&&(m=c(a),k.ns=m[0],a=m[1]);1<g.length&&("define"===q||"oneOrMore"===q||"zeroOrMore"===q||"optional"===q||"list"===q||"mixed"===q)&&(g=[{name:"group",e:h({name:"group",
e:g}).e}]);2<g.length&&"element"===q&&(g=[g[0]].concat({name:"group",e:h({name:"group",e:g.slice(1)}).e}));1===g.length&&"attribute"===q&&g.push({name:"text",text:a});1!==g.length||"choice"!==q&&"group"!==q&&"interleave"!==q?2<g.length&&("choice"===q||"group"===q||"interleave"===q)&&(g=h({name:q,e:g}).e):(q=g[0].name,w=g[0].names,k=g[0].a,a=g[0].text,g=g[0].e);"mixed"===q&&(q="interleave",g=[g[0],{name:"text"}]);"optional"===q&&(q="choice",g=[g[0],{name:"empty"}]);"zeroOrMore"===q&&(q="choice",g=
[{name:"oneOrMore",e:[g[0]]},{name:"empty"}]);if("define"===q&&k.combine){a:{u=k.combine;p=k.name;x=g;for(s=0;f&&s<f.length;s+=1)if(v=f[s],"define"===v.name&&v.a&&v.a.name===p){v.e=[{name:u,e:v.e.concat(x)}];f=v;break a}f=null}if(f)return}f={name:q};g&&0<g.length&&(f.e=g);for(m in k)if(k.hasOwnProperty(m)){f.a=k;break}void 0!==a&&(f.text=a);w&&0<w.length&&(f.names=w);"element"===q&&(f.id=b.length,b.push(f),f={name:"elementref",id:f.id});return f};this.parseRelaxNGDOM=function(c,h){var l=[],r=e(c&&
c.documentElement,l,void 0),k,m,q={};for(k=0;k<r.e.length;k+=1)m=r.e[k],"define"===m.name?q[m.a.name]=m:"start"===m.name&&(a=m);if(!a)return[new f("No Relax NG start element was found.")];g(a,q);for(k in q)q.hasOwnProperty(k)&&g(q[k],q);for(k=0;k<l.length;k+=1)g(l[k],q);h&&(p.rootPattern=h(a.e[0],l));b(a,l);for(k=0;k<l.length;k+=1)b(l[k],l);p.start=a;p.elements=l;p.nsmap=n;return null}};
// Input 22
runtime.loadClass("xmldom.RelaxNGParser");
xmldom.RelaxNG=function(){function f(a){return function(){var b;return function(){void 0===b&&(b=a());return b}}()}function h(a,b){return function(){var c={},d=0;return function(e){var f=e.hash||e.toString(),k;k=c[f];if(void 0!==k)return k;c[f]=k=b(e);k.hash=a+d.toString();d+=1;return k}}()}function c(a){return function(){var b={};return function(c){var d,e;e=b[c.localName];if(void 0===e)b[c.localName]=e={};else if(d=e[c.namespaceURI],void 0!==d)return d;return e[c.namespaceURI]=d=a(c)}}()}function g(a,
b,c){return function(){var d={},e=0;return function(f,k){var m=b&&b(f,k),l,q;if(void 0!==m)return m;m=f.hash||f.toString();l=k.hash||k.toString();q=d[m];if(void 0===q)d[m]=q={};else if(m=q[l],void 0!==m)return m;q[l]=m=c(f,k);m.hash=a+e.toString();e+=1;return m}}()}function b(a,c){"choice"===c.p1.type?b(a,c.p1):a[c.p1.hash]=c.p1;"choice"===c.p2.type?b(a,c.p2):a[c.p2.hash]=c.p2}function p(a,b){return{type:"element",nc:a,nullable:!1,textDeriv:function(){return s},startTagOpenDeriv:function(c){return a.contains(c)?
k(b,v):s},attDeriv:function(){return s},startTagCloseDeriv:function(){return this}}}function a(){return{type:"list",nullable:!1,hash:"list",textDeriv:function(){return v}}}function n(a,b,c,e){if(b===s)return s;if(e>=c.length)return b;0===e&&(e=0);for(var f=c.item(e);f.namespaceURI===d;){e+=1;if(e>=c.length)return b;f=c.item(e)}return f=n(a,b.attDeriv(a,c.item(e)),c,e+1)}function e(a,b,c){c.e[0].a?(a.push(c.e[0].text),b.push(c.e[0].a.ns)):e(a,b,c.e[0]);c.e[1].a?(a.push(c.e[1].text),b.push(c.e[1].a.ns)):
e(a,b,c.e[1])}var d="http://www.w3.org/2000/xmlns/",t,l,r,k,m,q,w,u,C,x,s={type:"notAllowed",nullable:!1,hash:"notAllowed",textDeriv:function(){return s},startTagOpenDeriv:function(){return s},attDeriv:function(){return s},startTagCloseDeriv:function(){return s},endTagDeriv:function(){return s}},v={type:"empty",nullable:!0,hash:"empty",textDeriv:function(){return s},startTagOpenDeriv:function(){return s},attDeriv:function(){return s},startTagCloseDeriv:function(){return v},endTagDeriv:function(){return s}},
y={type:"text",nullable:!0,hash:"text",textDeriv:function(){return y},startTagOpenDeriv:function(){return s},attDeriv:function(){return s},startTagCloseDeriv:function(){return y},endTagDeriv:function(){return s}},E,D,N;t=g("choice",function(a,b){if(a===s)return b;if(b===s||a===b)return a},function(a,d){var e={},k;b(e,{p1:a,p2:d});d=a=void 0;for(k in e)e.hasOwnProperty(k)&&(void 0===a?a=e[k]:d=void 0===d?e[k]:t(d,e[k]));return function(a,b){return{type:"choice",p1:a,p2:b,nullable:a.nullable||b.nullable,
textDeriv:function(c,d){return t(a.textDeriv(c,d),b.textDeriv(c,d))},startTagOpenDeriv:c(function(c){return t(a.startTagOpenDeriv(c),b.startTagOpenDeriv(c))}),attDeriv:function(c,d){return t(a.attDeriv(c,d),b.attDeriv(c,d))},startTagCloseDeriv:f(function(){return t(a.startTagCloseDeriv(),b.startTagCloseDeriv())}),endTagDeriv:f(function(){return t(a.endTagDeriv(),b.endTagDeriv())})}}(a,d)});l=function(a,b,c){return function(){var d={},e=0;return function(f,k){var m=b&&b(f,k),l,q;if(void 0!==m)return m;
m=f.hash||f.toString();l=k.hash||k.toString();m<l&&(q=m,m=l,l=q,q=f,f=k,k=q);q=d[m];if(void 0===q)d[m]=q={};else if(m=q[l],void 0!==m)return m;q[l]=m=c(f,k);m.hash=a+e.toString();e+=1;return m}}()}("interleave",function(a,b){if(a===s||b===s)return s;if(a===v)return b;if(b===v)return a},function(a,b){return{type:"interleave",p1:a,p2:b,nullable:a.nullable&&b.nullable,textDeriv:function(c,d){return t(l(a.textDeriv(c,d),b),l(a,b.textDeriv(c,d)))},startTagOpenDeriv:c(function(c){return t(E(function(a){return l(a,
b)},a.startTagOpenDeriv(c)),E(function(b){return l(a,b)},b.startTagOpenDeriv(c)))}),attDeriv:function(c,d){return t(l(a.attDeriv(c,d),b),l(a,b.attDeriv(c,d)))},startTagCloseDeriv:f(function(){return l(a.startTagCloseDeriv(),b.startTagCloseDeriv())})}});r=g("group",function(a,b){if(a===s||b===s)return s;if(a===v)return b;if(b===v)return a},function(a,b){return{type:"group",p1:a,p2:b,nullable:a.nullable&&b.nullable,textDeriv:function(c,d){var e=r(a.textDeriv(c,d),b);return a.nullable?t(e,b.textDeriv(c,
d)):e},startTagOpenDeriv:function(c){var d=E(function(a){return r(a,b)},a.startTagOpenDeriv(c));return a.nullable?t(d,b.startTagOpenDeriv(c)):d},attDeriv:function(c,d){return t(r(a.attDeriv(c,d),b),r(a,b.attDeriv(c,d)))},startTagCloseDeriv:f(function(){return r(a.startTagCloseDeriv(),b.startTagCloseDeriv())})}});k=g("after",function(a,b){if(a===s||b===s)return s},function(a,b){return{type:"after",p1:a,p2:b,nullable:!1,textDeriv:function(c,d){return k(a.textDeriv(c,d),b)},startTagOpenDeriv:c(function(c){return E(function(a){return k(a,
b)},a.startTagOpenDeriv(c))}),attDeriv:function(c,d){return k(a.attDeriv(c,d),b)},startTagCloseDeriv:f(function(){return k(a.startTagCloseDeriv(),b)}),endTagDeriv:f(function(){return a.nullable?b:s})}});m=h("oneormore",function(a){return a===s?s:{type:"oneOrMore",p:a,nullable:a.nullable,textDeriv:function(b,c){return r(a.textDeriv(b,c),t(this,v))},startTagOpenDeriv:function(b){var c=this;return E(function(a){return r(a,t(c,v))},a.startTagOpenDeriv(b))},attDeriv:function(b,c){return r(a.attDeriv(b,
c),t(this,v))},startTagCloseDeriv:f(function(){return m(a.startTagCloseDeriv())})}});w=g("attribute",void 0,function(a,b){return{type:"attribute",nullable:!1,nc:a,p:b,attDeriv:function(c,d){return a.contains(d)&&(b.nullable&&/^\s+$/.test(d.nodeValue)||b.textDeriv(c,d.nodeValue).nullable)?v:s},startTagCloseDeriv:function(){return s}}});q=h("value",function(a){return{type:"value",nullable:!1,value:a,textDeriv:function(b,c){return c===a?v:s},attDeriv:function(){return s},startTagCloseDeriv:function(){return this}}});
C=h("data",function(a){return{type:"data",nullable:!1,dataType:a,textDeriv:function(){return v},attDeriv:function(){return s},startTagCloseDeriv:function(){return this}}});E=function O(a,b){return"after"===b.type?k(b.p1,a(b.p2)):"choice"===b.type?t(O(a,b.p1),O(a,b.p2)):b};D=function(a,b,c){var d=c.currentNode;b=b.startTagOpenDeriv(d);b=n(a,b,d.attributes,0);var e=b=b.startTagCloseDeriv(),d=c.currentNode;b=c.firstChild();for(var f=[],k;b;)b.nodeType===Node.ELEMENT_NODE?f.push(b):b.nodeType!==Node.TEXT_NODE||
/^\s*$/.test(b.nodeValue)||f.push(b.nodeValue),b=c.nextSibling();0===f.length&&(f=[""]);k=e;for(e=0;k!==s&&e<f.length;e+=1)b=f[e],"string"===typeof b?k=/^\s*$/.test(b)?t(k,k.textDeriv(a,b)):k.textDeriv(a,b):(c.currentNode=b,k=D(a,k,c));c.currentNode=d;return b=k.endTagDeriv()};u=function(a){var b,c,d;if("name"===a.name)b=a.text,c=a.a.ns,a={name:b,ns:c,hash:"{"+c+"}"+b,contains:function(a){return a.namespaceURI===c&&a.localName===b}};else if("choice"===a.name){b=[];c=[];e(b,c,a);a="";for(d=0;d<b.length;d+=
1)a+="{"+c[d]+"}"+b[d]+",";a={hash:a,contains:function(a){var d;for(d=0;d<b.length;d+=1)if(b[d]===a.localName&&c[d]===a.namespaceURI)return!0;return!1}}}else a={hash:"anyName",contains:function(){return!0}};return a};x=function B(b,c){var d,e;if("elementref"===b.name){d=b.id||0;b=c[d];if(void 0!==b.name){var f=b;d=c[f.id]={hash:"element"+f.id.toString()};f=p(u(f.e[0]),x(f.e[1],c));for(e in f)f.hasOwnProperty(e)&&(d[e]=f[e]);return d}return b}switch(b.name){case "empty":return v;case "notAllowed":return s;
case "text":return y;case "choice":return t(B(b.e[0],c),B(b.e[1],c));case "interleave":d=B(b.e[0],c);for(e=1;e<b.e.length;e+=1)d=l(d,B(b.e[e],c));return d;case "group":return r(B(b.e[0],c),B(b.e[1],c));case "oneOrMore":return m(B(b.e[0],c));case "attribute":return w(u(b.e[0]),B(b.e[1],c));case "value":return q(b.text);case "data":return d=b.a&&b.a.type,void 0===d&&(d=""),C(d);case "list":return a()}throw"No support for "+b.name;};this.makePattern=function(a,b){var c={},d;for(d in b)b.hasOwnProperty(d)&&
(c[d]=b[d]);return d=x(a,c)};this.validate=function(a,b){var c;a.currentNode=a.root;c=D(null,N,a);c.nullable?b(null):(runtime.log("Error in Relax NG validation: "+c),b(["Error in Relax NG validation: "+c]))};this.init=function(a){N=a}};
// Input 23
runtime.loadClass("xmldom.RelaxNGParser");
xmldom.RelaxNG2=function(){function f(a,b){this.message=function(){b&&(a+=b.nodeType===Node.ELEMENT_NODE?" Element ":" Node ",a+=b.nodeName,b.nodeValue&&(a+=" with value '"+b.nodeValue+"'"),a+=".");return a}}function h(a,c,e,d){return"empty"===a.name?null:b(a,c,e,d)}function c(a,b){if(2!==a.e.length)throw"Element with wrong # of elements: "+a.e.length;for(var c=b.currentNode,d=c?c.nodeType:0,g=null;d>Node.ELEMENT_NODE;){if(d!==Node.COMMENT_NODE&&(d!==Node.TEXT_NODE||!/^\s+$/.test(b.currentNode.nodeValue)))return[new f("Not allowed node of type "+
d+".")];d=(c=b.nextSibling())?c.nodeType:0}if(!c)return[new f("Missing element "+a.names)];if(a.names&&-1===a.names.indexOf(p[c.namespaceURI]+":"+c.localName))return[new f("Found "+c.nodeName+" instead of "+a.names+".",c)];if(b.firstChild()){for(g=h(a.e[1],b,c);b.nextSibling();)if(d=b.currentNode.nodeType,!(b.currentNode&&b.currentNode.nodeType===Node.TEXT_NODE&&/^\s+$/.test(b.currentNode.nodeValue)||d===Node.COMMENT_NODE))return[new f("Spurious content.",b.currentNode)];if(b.parentNode()!==c)return[new f("Implementation error.")]}else g=
h(a.e[1],b,c);b.nextSibling();return g}var g,b,p;b=function(a,g,e,d){var p=a.name,l=null;if("text"===p)a:{for(var r=(a=g.currentNode)?a.nodeType:0;a!==e&&3!==r;){if(1===r){l=[new f("Element not allowed here.",a)];break a}r=(a=g.nextSibling())?a.nodeType:0}g.nextSibling();l=null}else if("data"===p)l=null;else if("value"===p)d!==a.text&&(l=[new f("Wrong value, should be '"+a.text+"', not '"+d+"'",e)]);else if("list"===p)l=null;else if("attribute"===p)a:{if(2!==a.e.length)throw"Attribute with wrong # of elements: "+
a.e.length;p=a.localnames.length;for(l=0;l<p;l+=1){d=e.getAttributeNS(a.namespaces[l],a.localnames[l]);""!==d||e.hasAttributeNS(a.namespaces[l],a.localnames[l])||(d=void 0);if(void 0!==r&&void 0!==d){l=[new f("Attribute defined too often.",e)];break a}r=d}l=void 0===r?[new f("Attribute not found: "+a.names,e)]:h(a.e[1],g,e,r)}else if("element"===p)l=c(a,g);else if("oneOrMore"===p){d=0;do r=g.currentNode,p=b(a.e[0],g,e),d+=1;while(!p&&r!==g.currentNode);1<d?(g.currentNode=r,l=null):l=p}else if("choice"===
p){if(2!==a.e.length)throw"Choice with wrong # of options: "+a.e.length;r=g.currentNode;if("empty"===a.e[0].name){if(p=b(a.e[1],g,e,d))g.currentNode=r;l=null}else{if(p=h(a.e[0],g,e,d))g.currentNode=r,p=b(a.e[1],g,e,d);l=p}}else if("group"===p){if(2!==a.e.length)throw"Group with wrong # of members: "+a.e.length;l=b(a.e[0],g,e)||b(a.e[1],g,e)}else if("interleave"===p)a:{r=a.e.length;d=[r];for(var k=r,m,q,w,u;0<k;){m=0;q=g.currentNode;for(l=0;l<r;l+=1)w=g.currentNode,!0!==d[l]&&d[l]!==w&&(u=a.e[l],(p=
b(u,g,e))?(g.currentNode=w,void 0===d[l]&&(d[l]=!1)):w===g.currentNode||"oneOrMore"===u.name||"choice"===u.name&&("oneOrMore"===u.e[0].name||"oneOrMore"===u.e[1].name)?(m+=1,d[l]=w):(m+=1,d[l]=!0));if(q===g.currentNode&&m===k){l=null;break a}if(0===m){for(l=0;l<r;l+=1)if(!1===d[l]){l=[new f("Interleave does not match.",e)];break a}l=null;break a}for(l=k=0;l<r;l+=1)!0!==d[l]&&(k+=1)}l=null}else throw p+" not allowed in nonEmptyPattern.";return l};this.validate=function(a,b){a.currentNode=a.root;var c=
h(g.e[0],a,a.root);b(c)};this.init=function(a,b){g=a;p=b}};
// Input 24
xmldom.XPathIterator=function(){};
xmldom.XPath=function(){function f(a,b,c){return-1!==a&&(a<b||-1===b)&&(a<c||-1===c)}function h(a){for(var b=[],c=0,d=a.length,e;c<d;){var g=a,h=d,p=b,n="",s=[],v=g.indexOf("[",c),y=g.indexOf("/",c),E=g.indexOf("=",c);f(y,v,E)?(n=g.substring(c,y),c=y+1):f(v,y,E)?(n=g.substring(c,v),c=t(g,v,s)):f(E,y,v)?(n=g.substring(c,E),c=E):(n=g.substring(c,h),c=h);p.push({location:n,predicates:s});if(c<d&&"="===a[c]){e=a.substring(c+1,d);if(2<e.length&&("'"===e[0]||'"'===e[0]))e=e.slice(1,e.length-1);else try{e=
parseInt(e,10)}catch(D){}c=d}}return{steps:b,value:e}}function c(){var a,b=!1;this.setNode=function(b){a=b};this.reset=function(){b=!1};this.next=function(){var c=b?null:a;b=!0;return c}}function g(a,b,c){this.reset=function(){a.reset()};this.next=function(){for(var d=a.next();d&&!(d=d.getAttributeNodeNS(b,c));)d=a.next();return d}}function b(a,b){var c=a.next(),d=null;this.reset=function(){a.reset();c=a.next();d=null};this.next=function(){for(;c;){if(d)if(b&&d.firstChild)d=d.firstChild;else{for(;!d.nextSibling&&
d!==c;)d=d.parentNode;d===c?c=a.next():d=d.nextSibling}else{do(d=c.firstChild)||(c=a.next());while(c&&!d)}if(d&&d.nodeType===Node.ELEMENT_NODE)return d}return null}}function p(a,b){this.reset=function(){a.reset()};this.next=function(){for(var c=a.next();c&&!b(c);)c=a.next();return c}}function a(a,b,c){b=b.split(":",2);var d=c(b[0]),e=b[1];return new p(a,function(a){return a.localName===e&&a.namespaceURI===d})}function n(a,b,e){var f=new c,q=d(f,b,e),g=b.value;return void 0===g?new p(a,function(a){f.setNode(a);
q.reset();return q.next()}):new p(a,function(a){f.setNode(a);q.reset();return(a=q.next())&&a.nodeValue===g})}function e(a,b,e){var f=a.ownerDocument,g=[],p=null;if(f&&f.evaluate)for(e=f.evaluate(b,a,e,XPathResult.UNORDERED_NODE_ITERATOR_TYPE,null),p=e.iterateNext();null!==p;)p.nodeType===Node.ELEMENT_NODE&&g.push(p),p=e.iterateNext();else{g=new c;g.setNode(a);a=h(b);g=d(g,a,e);a=[];for(e=g.next();e;)a.push(e),e=g.next();g=a}return g}var d,t;t=function(a,b,c){for(var d=b,e=a.length,f=0;d<e;)"]"===
a[d]?(f-=1,0>=f&&c.push(h(a.substring(b,d)))):"["===a[d]&&(0>=f&&(b=d+1),f+=1),d+=1;return d};xmldom.XPathIterator.prototype.next=function(){};xmldom.XPathIterator.prototype.reset=function(){};d=function(c,d,e){var f,q,h,u;for(f=0;f<d.steps.length;f+=1)for(h=d.steps[f],q=h.location,""===q?c=new b(c,!1):"@"===q[0]?(u=q.slice(1).split(":",2),c=new g(c,e(u[0]),u[1])):"."!==q&&(c=new b(c,!1),-1!==q.indexOf(":")&&(c=a(c,q,e))),q=0;q<h.predicates.length;q+=1)u=h.predicates[q],c=n(c,u,e);return c};xmldom.XPath=
function(){this.getODFElementsWithXPath=e};return xmldom.XPath}();
// Input 25
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
gui.AnnotationViewManager=function(f,h,c){function g(a){var b=a.node,c=a.end;a=e.createRange();c&&(a.setStart(b,b.childNodes.length),a.setEnd(c,0),c=d.getTextNodes(a,!1),c.forEach(function(a){var c=e.createElement("span");c.className="annotationHighlight";c.setAttribute("annotation",b.getAttributeNS(odf.Namespaces.officens,"name"));a.parentNode.insertBefore(c,a);c.appendChild(a)}));a.detach()}function b(a){var b=f.getSizer();a?(c.style.display="inline-block",b.style.paddingRight=t.getComputedStyle(c).width):
(c.style.display="none",b.style.paddingRight=0);f.refreshSize()}function p(){n.sort(function(a,b){return a.node.compareDocumentPosition(b.node)===Node.DOCUMENT_POSITION_FOLLOWING?-1:1})}function a(){var a;for(a=0;a<n.length;a+=1){var b=n[a],d=b.node.parentNode,m=d.nextSibling,g=m.nextSibling,h=d.parentNode,u=0,p=n[n.indexOf(b)-1],x=void 0,b=b.node.getElementsByTagNameNS(odf.Namespaces.dcns,"creator")[0],u=void 0,u=f.getZoomLevel();d.style.left=(c.getBoundingClientRect().left-h.getBoundingClientRect().left)/
u+"px";d.style.width=c.getBoundingClientRect().width/u+"px";m.style.width=parseFloat(d.style.left)-30+"px";p&&(x=p.node.parentNode.getBoundingClientRect(),20>=(h.getBoundingClientRect().top-x.bottom)/u?d.style.top=Math.abs(h.getBoundingClientRect().top-x.bottom)/u+20+"px":d.style.top="0px");g.style.left=m.getBoundingClientRect().width/u+"px";var m=g.style,h=g.getBoundingClientRect().left/u,p=g.getBoundingClientRect().top/u,x=d.getBoundingClientRect().left/u,s=d.getBoundingClientRect().top/u,v=0,y=
0,v=x-h,v=v*v,y=s-p,y=y*y,h=Math.sqrt(v+y);m.width=h+"px";u=Math.asin((d.getBoundingClientRect().top-g.getBoundingClientRect().top)/(u*parseFloat(g.style.width)));g.style.transform="rotate("+u+"rad)";g.style.MozTransform="rotate("+u+"rad)";g.style.WebkitTransform="rotate("+u+"rad)";g.style.msTransform="rotate("+u+"rad)";b&&(u=t.getComputedStyle(b,":before").content)&&"none"!==u&&(u=u.substring(1,u.length-1),b.firstChild?b.firstChild.nodeValue=u:b.appendChild(e.createTextNode(u)))}}var n=[],e=h.ownerDocument,
d=new odf.OdfUtils,t=runtime.getWindow();runtime.assert(Boolean(t),"Expected to be run in an environment which has a global window, like a browser.");this.rerenderAnnotations=a;this.addAnnotation=function(c){b(!0);n.push({node:c.node,end:c.end});p();var d=e.createElement("div"),f=e.createElement("div"),m=e.createElement("div"),q=e.createElement("div"),h=e.createElement("div"),u=c.node;d.className="annotationWrapper";u.parentNode.insertBefore(d,u);f.className="annotationNote";f.appendChild(u);h.className=
"annotationRemoveButton";f.appendChild(h);m.className="annotationConnector horizontal";q.className="annotationConnector angular";d.appendChild(f);d.appendChild(m);d.appendChild(q);c.end&&g(c);a()};this.forgetAnnotations=function(){for(;n.length;){var a=n[0],c=n.indexOf(a),d=a.node,f=d.parentNode.parentNode;"div"===f.localName&&(f.parentNode.insertBefore(d,f),f.parentNode.removeChild(f));a=a.node.getAttributeNS(odf.Namespaces.officens,"name");a=e.querySelectorAll('span.annotationHighlight[annotation="'+
a+'"]');f=d=void 0;for(d=0;d<a.length;d+=1){for(f=a[d];f.firstChild;)f.parentNode.insertBefore(f.firstChild,f);f.parentNode.removeChild(f)}-1!==c&&n.splice(c,1);0===n.length&&b(!1)}}};
// Input 26
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
odf.OdfNodeFilter=function(){this.acceptNode=function(f){return"http://www.w3.org/1999/xhtml"===f.namespaceURI?NodeFilter.FILTER_SKIP:f.namespaceURI&&f.namespaceURI.match(/^urn:webodf:/)?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}};
// Input 27
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
odf.Namespaces=function(){function f(c){return h[c]||null}var h={draw:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",fo:"urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",office:"urn:oasis:names:tc:opendocument:xmlns:office:1.0",presentation:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",style:"urn:oasis:names:tc:opendocument:xmlns:style:1.0",svg:"urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",table:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",text:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
dr3d:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",numberns:"urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",xlink:"http://www.w3.org/1999/xlink",xml:"http://www.w3.org/XML/1998/namespace",dc:"http://purl.org/dc/elements/1.1/",webodf:"urn:webodf"},c;f.lookupNamespaceURI=f;c=function(){};c.forEachPrefix=function(c){for(var b in h)h.hasOwnProperty(b)&&c(b,h[b])};c.resolvePrefix=f;c.namespaceMap=h;c.drawns="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0";c.fons="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0";
c.officens="urn:oasis:names:tc:opendocument:xmlns:office:1.0";c.presentationns="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0";c.stylens="urn:oasis:names:tc:opendocument:xmlns:style:1.0";c.svgns="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0";c.tablens="urn:oasis:names:tc:opendocument:xmlns:table:1.0";c.textns="urn:oasis:names:tc:opendocument:xmlns:text:1.0";c.dr3dns="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0";c.numberns="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0";
c.xlinkns="http://www.w3.org/1999/xlink";c.xmlns="http://www.w3.org/XML/1998/namespace";c.dcns="http://purl.org/dc/elements/1.1/";c.webodfns="urn:webodf";return c}();
// Input 28
runtime.loadClass("xmldom.XPath");
odf.StyleInfo=function(){function f(a,b){for(var c=r[a.localName],d=c&&c[a.namespaceURI],e=d?d.length:0,k,c=0;c<e;c+=1)(k=a.getAttributeNS(d[c].ns,d[c].localname))&&a.setAttributeNS(d[c].ns,t[d[c].ns]+d[c].localname,b+k);for(c=a.firstChild;c;)c.nodeType===Node.ELEMENT_NODE&&(d=c,f(d,b)),c=c.nextSibling}function h(a,b){for(var c=r[a.localName],d=c&&c[a.namespaceURI],e=d?d.length:0,f,c=0;c<e;c+=1)if(f=a.getAttributeNS(d[c].ns,d[c].localname))f=f.replace(b,""),a.setAttributeNS(d[c].ns,t[d[c].ns]+d[c].localname,
f);for(c=a.firstChild;c;)c.nodeType===Node.ELEMENT_NODE&&(d=c,h(d,b)),c=c.nextSibling}function c(a,b){var c=r[a.localName],d=(c=c&&c[a.namespaceURI])?c.length:0,e,f,k;for(k=0;k<d;k+=1)if(e=a.getAttributeNS(c[k].ns,c[k].localname))b=b||{},f=c[k].keyname,f=b[f]=b[f]||{},f[e]=1;return b}function g(a,b){var d,e;c(a,b);for(d=a.firstChild;d;)d.nodeType===Node.ELEMENT_NODE&&(e=d,g(e,b)),d=d.nextSibling}function b(a,b,c){this.key=a;this.name=b;this.family=c;this.requires={}}function p(a,c,d){var e=a+'"'+
c,f=d[e];f||(f=d[e]=new b(e,a,c));return f}function a(b,c,e){var f=r[b.localName],k=(f=f&&f[b.namespaceURI])?f.length:0,g=b.getAttributeNS(d,"name"),l=b.getAttributeNS(d,"family"),h;g&&l&&(c=p(g,l,e));if(c)for(g=0;g<k;g+=1)if(l=b.getAttributeNS(f[g].ns,f[g].localname))h=f[g].keyname,l=p(l,h,e),c.requires[l.key]=l;for(g=b.firstChild;g;)g.nodeType===Node.ELEMENT_NODE&&(b=g,a(b,c,e)),g=g.nextSibling;return e}function n(a,b){var c=b[a.family];c||(c=b[a.family]={});c[a.name]=1;Object.keys(a.requires).forEach(function(c){n(a.requires[c],
b)})}function e(b,c){var d=a(b,null,{});Object.keys(d).forEach(function(a){a=d[a];var b=c[a.family];b&&b.hasOwnProperty(a.name)&&n(a,c)})}var d="urn:oasis:names:tc:opendocument:xmlns:style:1.0",t={"urn:oasis:names:tc:opendocument:xmlns:chart:1.0":"chart:","urn:oasis:names:tc:opendocument:xmlns:database:1.0":"db:","urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0":"dr3d:","urn:oasis:names:tc:opendocument:xmlns:drawing:1.0":"draw:","urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0":"fo:","urn:oasis:names:tc:opendocument:xmlns:form:1.0":"form:",
"urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0":"number:","urn:oasis:names:tc:opendocument:xmlns:office:1.0":"office:","urn:oasis:names:tc:opendocument:xmlns:presentation:1.0":"presentation:","urn:oasis:names:tc:opendocument:xmlns:style:1.0":"style:","urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0":"svg:","urn:oasis:names:tc:opendocument:xmlns:table:1.0":"table:","urn:oasis:names:tc:opendocument:xmlns:text:1.0":"chart:","http://www.w3.org/XML/1998/namespace":"xml:"},l={text:[{ens:d,
en:"tab-stop",ans:d,a:"leader-text-style"},{ens:d,en:"drop-cap",ans:d,a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"notes-configuration",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"citation-body-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"notes-configuration",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"citation-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"a",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"alphabetical-index",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"linenumbering-configuration",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"list-level-style-number",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
en:"ruby-text",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"span",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"a",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"visited-style-name"},{ens:d,en:"text-properties",ans:d,a:"text-line-through-text-style"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"alphabetical-index-source",
ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"main-entry-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-bibliography",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-chapter",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-link-end",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-link-start",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-page-number",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-span",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
en:"index-entry-tab-stop",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-entry-text",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-title-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"list-level-style-bullet",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"outline-level-style",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"}],paragraph:[{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"caption",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"circle",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
en:"connector",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"control",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"custom-shape",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"ellipse",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"frame",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"line",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"measure",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
en:"path",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"polygon",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"polyline",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"rect",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"regular-polygon",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:office:1.0",en:"annotation",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"text-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:form:1.0",en:"column",ans:"urn:oasis:names:tc:opendocument:xmlns:form:1.0",a:"text-style-name"},{ens:d,en:"style",ans:d,a:"next-style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"body",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"even-columns",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"even-rows",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
en:"first-column",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"first-row",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"last-column",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"last-row",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"odd-columns",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"odd-rows",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"paragraph-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"notes-configuration",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"default-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
en:"alphabetical-index-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"bibliography-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"h",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"illustration-index-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-source-style",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"object-index-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"p",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
en:"table-index-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"table-of-content-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"table-index-entry-template",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"user-index-entry-template",
ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:d,en:"page-layout-properties",ans:d,a:"register-truth-ref-style-name"}],chart:[{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"axis",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"chart",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"data-label",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"data-point",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"equation",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"error-indicator",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"floor",
ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"footer",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"grid",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"legend",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
en:"mean-value",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"plot-area",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"regression-curve",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"series",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"stock-gain-marker",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"stock-loss-marker",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"stock-range-line",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"subtitle",
ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"title",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",en:"wall",ans:"urn:oasis:names:tc:opendocument:xmlns:chart:1.0",a:"style-name"}],section:[{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"alphabetical-index",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
en:"bibliography",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"illustration-index",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"index-title",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"object-index",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"section",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"table-of-content",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"table-index",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"user-index",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
a:"style-name"}],ruby:[{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"ruby",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"}],table:[{ens:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",en:"query",ans:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",en:"table-representation",ans:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
en:"background",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"table",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"}],"table-column":[{ens:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",en:"column",ans:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"table-column",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
a:"style-name"}],"table-row":[{ens:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",en:"query",ans:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",a:"default-row-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",en:"table-representation",ans:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",a:"default-row-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"table-row",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"}],"table-cell":[{ens:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",
en:"column",ans:"urn:oasis:names:tc:opendocument:xmlns:database:1.0",a:"default-cell-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"table-column",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"default-cell-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"table-row",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"default-cell-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"body",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"covered-table-cell",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"even-columns",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"covered-table-cell",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
en:"even-columns",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"even-rows",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"first-column",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"first-row",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"last-column",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"last-row",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"odd-columns",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"odd-rows",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",en:"table-cell",ans:"urn:oasis:names:tc:opendocument:xmlns:table:1.0",a:"style-name"}],graphic:[{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"cube",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"extrude",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"rotate",
ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"scene",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"sphere",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"caption",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
en:"circle",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"connector",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"control",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"custom-shape",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"ellipse",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"frame",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"g",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"line",
ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"measure",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"page-thumbnail",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"path",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"polygon",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"polyline",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"rect",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"regular-polygon",
ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:office:1.0",en:"annotation",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"}],presentation:[{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"cube",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"extrude",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"rotate",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"scene",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",en:"sphere",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"caption",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"circle",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"connector",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"control",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
en:"custom-shape",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"ellipse",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"frame",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"g",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"line",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"measure",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"page-thumbnail",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
en:"path",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"polygon",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"polyline",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"rect",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"regular-polygon",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:office:1.0",en:"annotation",ans:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",a:"style-name"}],"drawing-page":[{ens:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",en:"page",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
en:"notes",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:d,en:"handout-master",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"},{ens:d,en:"master-page",ans:"urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",a:"style-name"}],"list-style":[{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"list",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"numbered-paragraph",
ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"list-item",ans:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",a:"style-override"},{ens:d,en:"style",ans:d,a:"list-style-name"}],data:[{ens:d,en:"style",ans:d,a:"data-style-name"},{ens:d,en:"style",ans:d,a:"percentage-data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",en:"date-time-decl",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
en:"creation-date",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"creation-time",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"database-display",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"date",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"editing-duration",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"expression",
ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"meta-field",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"modification-date",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"modification-time",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"print-date",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"print-time",ans:d,
a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"table-formula",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"time",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"user-defined",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"user-field-get",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"user-field-input",ans:d,a:"data-style-name"},
{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"variable-get",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"variable-input",ans:d,a:"data-style-name"},{ens:"urn:oasis:names:tc:opendocument:xmlns:text:1.0",en:"variable-set",ans:d,a:"data-style-name"}],"page-layout":[{ens:"urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",en:"notes",ans:d,a:"page-layout-name"},{ens:d,en:"handout-master",ans:d,a:"page-layout-name"},{ens:d,en:"master-page",ans:d,
a:"page-layout-name"}]},r,k=new xmldom.XPath;this.UsedStyleList=function(a,b){var c={};this.uses=function(a){var b=a.localName,e=a.getAttributeNS("urn:oasis:names:tc:opendocument:xmlns:drawing:1.0","name")||a.getAttributeNS(d,"name");a="style"===b?a.getAttributeNS(d,"family"):"urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0"===a.namespaceURI?"data":b;return(a=c[a])?0<a[e]:!1};g(a,c);b&&e(b,c)};this.hasDerivedStyles=function(a,b,c){var d=b("style"),e=c.getAttributeNS(d,"name");c=c.getAttributeNS(d,
"family");return k.getODFElementsWithXPath(a,"//style:*[@style:parent-style-name='"+e+"'][@style:family='"+c+"']",b).length?!0:!1};this.prefixStyleNames=function(a,b,c){var e;if(a){for(e=a.firstChild;e;){if(e.nodeType===Node.ELEMENT_NODE){var k=e,g=b,l=k.getAttributeNS("urn:oasis:names:tc:opendocument:xmlns:drawing:1.0","name"),h=void 0;l?h="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0":(l=k.getAttributeNS(d,"name"))&&(h=d);h&&k.setAttributeNS(h,t[h]+"name",g+l)}e=e.nextSibling}f(a,b);c&&f(c,
b)}};this.removePrefixFromStyleNames=function(a,b,c){var e=RegExp("^"+b);if(a){for(b=a.firstChild;b;){if(b.nodeType===Node.ELEMENT_NODE){var f=b,k=e,g=f.getAttributeNS("urn:oasis:names:tc:opendocument:xmlns:drawing:1.0","name"),l=void 0;g?l="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0":(g=f.getAttributeNS(d,"name"))&&(l=d);l&&(g=g.replace(k,""),f.setAttributeNS(l,t[l]+"name",g))}b=b.nextSibling}h(a,e);c&&h(c,e)}};this.determineStylesForNode=c;r=function(a){var b,c,d,e,f,k={},g;for(b in a)if(a.hasOwnProperty(b))for(e=
a[b],d=e.length,c=0;c<d;c+=1)f=e[c],g=k[f.en]=k[f.en]||{},g=g[f.ens]=g[f.ens]||[],g.push({ns:f.ans,localname:f.a,keyname:b});return k}(l)};
// Input 29
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.DomUtils");
odf.OdfUtils=function(){function f(a){var b=a&&a.localName;return("p"===b||"h"===b)&&a.namespaceURI===w}function h(a){for(;a&&!f(a);)a=a.parentNode;return a}function c(a){return/^[ \t\r\n]+$/.test(a)}function g(a){var b=a&&a.localName;return/^(span|p|h|a|meta)$/.test(b)&&a.namespaceURI===w||"span"===b&&"annotationHighlight"===a.className?!0:!1}function b(a){var b=a&&a.localName,c,d=!1;b&&(c=a.namespaceURI,c===w?d="s"===b||"tab"===b||"line-break"===b:c===u&&(d="frame"===b&&"as-char"===a.getAttributeNS(w,
"anchor-type")));return d}function p(a){for(;null!==a.firstChild&&g(a);)a=a.firstChild;return a}function a(a){for(;null!==a.lastChild&&g(a);)a=a.lastChild;return a}function n(b){for(;!f(b)&&null===b.previousSibling;)b=b.parentNode;return f(b)?null:a(b.previousSibling)}function e(a){for(;!f(a)&&null===a.nextSibling;)a=a.parentNode;return f(a)?null:p(a.nextSibling)}function d(a){for(var d=!1;a;)if(a.nodeType===Node.TEXT_NODE)if(0===a.length)a=n(a);else return!c(a.data.substr(a.length-1,1));else b(a)?
(d=!0,a=null):a=n(a);return d}function t(a){var d=!1;for(a=a&&p(a);a;){if(a.nodeType===Node.TEXT_NODE&&0<a.length&&!c(a.data)){d=!0;break}if(b(a)){d=!0;break}a=e(a)}return d}function l(a,b){return c(a.data.substr(b))?!t(e(a)):!1}function r(a,e){var f=a.data,k;if(!c(f[e])||b(a.parentNode))return!1;0<e?c(f[e-1])||(k=!0):d(n(a))&&(k=!0);return!0===k?l(a,e)?!1:!0:!1}function k(a){return(a=/-?([0-9]*[0-9][0-9]*(\.[0-9]*)?|0+\.[0-9]*[1-9][0-9]*|\.[0-9]*[1-9][0-9]*)((cm)|(mm)|(in)|(pt)|(pc)|(px)|(%))/.exec(a))?
{value:parseFloat(a[1]),unit:a[3]}:null}function m(a){return(a=k(a))&&"%"!==a.unit?null:a}function q(a){switch(a.namespaceURI){case odf.Namespaces.drawns:case odf.Namespaces.svgns:case odf.Namespaces.dr3dns:return!1;case odf.Namespaces.textns:switch(a.localName){case "note-body":case "ruby-text":return!1}break;case odf.Namespaces.officens:switch(a.localName){case "annotation":case "binary-data":case "event-listeners":return!1}break;default:switch(a.localName){case "editinfo":return!1}}return!0}var w=
"urn:oasis:names:tc:opendocument:xmlns:text:1.0",u="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",C=/^\s*$/,x=new core.DomUtils;this.isParagraph=f;this.getParagraphElement=h;this.isWithinTrackedChanges=function(a,b){for(;a&&a!==b;){if(a.namespaceURI===w&&"tracked-changes"===a.localName)return!0;a=a.parentNode}return!1};this.isListItem=function(a){return"list-item"===(a&&a.localName)&&a.namespaceURI===w};this.isODFWhitespace=c;this.isGroupingElement=g;this.isCharacterElement=b;this.firstChild=
p;this.lastChild=a;this.previousNode=n;this.nextNode=e;this.scanLeftForNonWhitespace=d;this.lookLeftForCharacter=function(a){var e;e=0;a.nodeType===Node.TEXT_NODE&&0<a.length?(e=a.data,e=c(e.substr(e.length-1,1))?1===e.length?d(n(a))?2:0:c(e.substr(e.length-2,1))?0:2:1):b(a)&&(e=1);return e};this.lookRightForCharacter=function(a){var d=!1;a&&a.nodeType===Node.TEXT_NODE&&0<a.length?d=!c(a.data.substr(0,1)):b(a)&&(d=!0);return d};this.scanLeftForAnyCharacter=function(d){var e=!1;for(d=d&&a(d);d;){if(d.nodeType===
Node.TEXT_NODE&&0<d.length&&!c(d.data)){e=!0;break}if(b(d)){e=!0;break}d=n(d)}return e};this.scanRightForAnyCharacter=t;this.isTrailingWhitespace=l;this.isSignificantWhitespace=r;this.getFirstNonWhitespaceChild=function(a){for(a=a&&a.firstChild;a&&a.nodeType===Node.TEXT_NODE&&C.test(a.nodeValue);)a=a.nextSibling;return a};this.parseLength=k;this.parseFoFontSize=function(a){var b;b=(b=k(a))&&(0>=b.value||"%"===b.unit)?null:b;return b||m(a)};this.parseFoLineHeight=function(a){var b;b=(b=k(a))&&(0>b.value||
"%"===b.unit)?null:b;return b||m(a)};this.getImpactedParagraphs=function(a){var b=a.commonAncestorContainer,c=[];for(b.nodeType===Node.ELEMENT_NODE&&(c=x.getElementsByTagNameNS(b,w,"p").concat(x.getElementsByTagNameNS(b,w,"h")));b&&!f(b);)b=b.parentNode;b&&c.push(b);return c.filter(function(b){return x.rangeIntersectsNode(a,b)})};this.getTextNodes=function(a,b){var d=a.startContainer.ownerDocument.createRange(),e;e=x.getNodesInRange(a,function(e){d.selectNodeContents(e);if(e.nodeType===Node.TEXT_NODE){if(b&&
x.rangesIntersect(a,d)||x.containsRange(a,d))return Boolean(h(e)&&(!c(e.textContent)||r(e,0)))?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT}else if(x.rangesIntersect(a,d)&&q(e))return NodeFilter.FILTER_SKIP;return NodeFilter.FILTER_REJECT});d.detach();return e};this.getTextElements=function(a,d){var e=a.startContainer.ownerDocument.createRange(),f;f=x.getNodesInRange(a,function(f){var k=f.nodeType;e.selectNodeContents(f);if(k===Node.TEXT_NODE){if(x.containsRange(a,e)&&(d||Boolean(h(f)&&(!c(f.textContent)||
r(f,0)))))return NodeFilter.FILTER_ACCEPT}else if(b(f)){if(x.containsRange(a,e))return NodeFilter.FILTER_ACCEPT}else if(q(f)||g(f))return NodeFilter.FILTER_SKIP;return NodeFilter.FILTER_REJECT});e.detach();return f};this.getParagraphElements=function(a){var b=a.startContainer.ownerDocument.createRange(),c;c=x.getNodesInRange(a,function(c){b.selectNodeContents(c);if(f(c)){if(x.rangesIntersect(a,b))return NodeFilter.FILTER_ACCEPT}else if(q(c)||g(c))return NodeFilter.FILTER_SKIP;return NodeFilter.FILTER_REJECT});
b.detach();return c}};
// Input 30
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("odf.OdfUtils");
odf.TextSerializer=function(){function f(g){var b="",p=h.filter?h.filter.acceptNode(g):NodeFilter.FILTER_ACCEPT,a=g.nodeType,n;if(p===NodeFilter.FILTER_ACCEPT||p===NodeFilter.FILTER_SKIP)for(n=g.firstChild;n;)b+=f(n),n=n.nextSibling;p===NodeFilter.FILTER_ACCEPT&&(a===Node.ELEMENT_NODE&&c.isParagraph(g)?b+="\n":a===Node.TEXT_NODE&&g.textContent&&(b+=g.textContent));return b}var h=this,c=new odf.OdfUtils;this.filter=null;this.writeToString=function(c){return c?f(c):""}};
// Input 31
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.DomUtils");runtime.loadClass("core.LoopWatchDog");runtime.loadClass("odf.Namespaces");
odf.TextStyleApplicator=function(f,h,c){function g(a){function b(a,c){return"object"===typeof a&&"object"===typeof c?Object.keys(a).every(function(d){return b(a[d],c[d])}):a===c}this.isStyleApplied=function(c){c=h.getAppliedStylesForElement(c);return b(a,c)}}function b(b){var g={};this.applyStyleToContainer=function(l){var p;p=l.getAttributeNS(a,"style-name");var k=l.ownerDocument;p=p||"";if(!g.hasOwnProperty(p)){var m=p,q=p,w;q?(w=h.getStyleElement(q,"text"),w.parentNode===c?k=w.cloneNode(!0):(k=
k.createElementNS(n,"style:style"),k.setAttributeNS(n,"style:parent-style-name",q),k.setAttributeNS(n,"style:family","text"),k.setAttributeNS(e,"scope","document-content"))):(k=k.createElementNS(n,"style:style"),k.setAttributeNS(n,"style:family","text"),k.setAttributeNS(e,"scope","document-content"));h.updateStyle(k,b,f);c.appendChild(k);g[m]=k}p=g[p].getAttributeNS(n,"name");l.setAttributeNS(a,"text:style-name",p)}}var p=new core.DomUtils,a=odf.Namespaces.textns,n=odf.Namespaces.stylens,e="urn:webodf:names:scope";
this.applyStyle=function(c,e,f){var h={},k,m,q,n;runtime.assert(f&&f["style:text-properties"],"applyStyle without any text properties");h["style:text-properties"]=f["style:text-properties"];q=new b(h);n=new g(h);c.forEach(function(b){k=n.isStyleApplied(b);if(!1===k){var c=b.ownerDocument,d=b.parentNode,f,g=b,l=new core.LoopWatchDog(1E3);"span"===d.localName&&d.namespaceURI===a?(b.previousSibling&&!p.rangeContainsNode(e,b.previousSibling)?(c=d.cloneNode(!1),d.parentNode.insertBefore(c,d.nextSibling)):
c=d,f=!0):(c=c.createElementNS(a,"text:span"),d.insertBefore(c,b),f=!1);for(;g&&(g===b||p.rangeContainsNode(e,g));)l.check(),d=g.nextSibling,g.parentNode!==c&&c.appendChild(g),g=d;if(g&&f)for(b=c.cloneNode(!1),c.parentNode.insertBefore(b,c.nextSibling);g;)l.check(),d=g.nextSibling,b.appendChild(g),g=d;m=c;q.applyStyleToContainer(m)}})}};
// Input 32
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("odf.Namespaces");runtime.loadClass("odf.OdfUtils");runtime.loadClass("xmldom.XPath");runtime.loadClass("core.CSSUnits");
odf.Style2CSS=function(){function f(a){var b={},c,d;if(!a)return b;for(a=a.firstChild;a;){if(d=a.namespaceURI!==m||"style"!==a.localName&&"default-style"!==a.localName?a.namespaceURI===u&&"list-style"===a.localName?"list":a.namespaceURI!==m||"page-layout"!==a.localName&&"default-page-layout"!==a.localName?void 0:"page":a.getAttributeNS(m,"family"))(c=a.getAttributeNS&&a.getAttributeNS(m,"name"))||(c=""),d=b[d]=b[d]||{},d[c]=a;a=a.nextSibling}return b}function h(a,b){if(!b||!a)return null;if(a[b])return a[b];
var c,d;for(c in a)if(a.hasOwnProperty(c)&&(d=h(a[c].derivedStyles,b)))return d;return null}function c(a,b,d){var e=b[a],f,g;e&&(f=e.getAttributeNS(m,"parent-style-name"),g=null,f&&(g=h(d,f),!g&&b[f]&&(c(f,b,d),g=b[f],b[f]=null)),g?(g.derivedStyles||(g.derivedStyles={}),g.derivedStyles[a]=e):d[a]=e)}function g(a,b){for(var d in a)a.hasOwnProperty(d)&&(c(d,a,b),a[d]=null)}function b(a,b){var c=s[a],d;if(null===c)return null;d=b?"["+c+'|style-name="'+b+'"]':"["+c+"|style-name]";"presentation"===c&&
(c="draw",d=b?'[presentation|style-name="'+b+'"]':"[presentation|style-name]");return c+"|"+v[a].join(d+","+c+"|")+d}function p(a,c,d){var e=[],f,g;e.push(b(a,c));for(f in d.derivedStyles)if(d.derivedStyles.hasOwnProperty(f))for(g in c=p(a,f,d.derivedStyles[f]),c)c.hasOwnProperty(g)&&e.push(c[g]);return e}function a(a,b,c){if(!a)return null;for(a=a.firstChild;a;){if(a.namespaceURI===b&&a.localName===c)return b=a;a=a.nextSibling}return null}function n(a,b){var c="",d,e;for(d in b)if(b.hasOwnProperty(d)&&
(d=b[d],e=a.getAttributeNS(d[0],d[1]))){e=e.trim();if(fa.hasOwnProperty(d[1])){var f=e.indexOf(" "),g=void 0,k=void 0;-1!==f?(g=e.substring(0,f),k=e.substring(f)):(g=e,k="");(g=ba.parseLength(g))&&("pt"===g.unit&&0.75>g.value)&&(e="0.75pt"+k)}d[2]&&(c+=d[2]+":"+e+";")}return c}function e(b){return(b=a(b,m,"text-properties"))?ba.parseFoFontSize(b.getAttributeNS(k,"font-size")):null}function d(a){a=a.replace(/^#?([a-f\d])([a-f\d])([a-f\d])$/i,function(a,b,c,d){return b+b+c+c+d+d});return(a=/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(a))?
{r:parseInt(a[1],16),g:parseInt(a[2],16),b:parseInt(a[3],16)}:null}function t(a,b,c,d){b='text|list[text|style-name="'+b+'"]';var e=c.getAttributeNS(u,"level"),f;c=ba.getFirstNonWhitespaceChild(c);c=ba.getFirstNonWhitespaceChild(c);var g;c&&(f=c.attributes,g=f["fo:text-indent"]?f["fo:text-indent"].value:void 0,f=f["fo:margin-left"]?f["fo:margin-left"].value:void 0);g||(g="-0.6cm");c="-"===g.charAt(0)?g.substring(1):"-"+g;for(e=e&&parseInt(e,10);1<e;)b+=" > text|list-item > text|list",e-=1;e=b+" > text|list-item > *:not(text|list):first-child";
void 0!==f&&(f=e+"{margin-left:"+f+";}",a.insertRule(f,a.cssRules.length));d=b+" > text|list-item > *:not(text|list):first-child:before{"+d+";";d+="counter-increment:list;";d+="margin-left:"+g+";";d+="width:"+c+";";d+="display:inline-block}";try{a.insertRule(d,a.cssRules.length)}catch(k){throw k;}}function l(b,c,f,g){if("list"===c)for(var h=g.firstChild,q,s;h;){if(h.namespaceURI===u)if(q=h,"list-level-style-number"===h.localName){var v=q;s=v.getAttributeNS(m,"num-format");var K=v.getAttributeNS(m,
"num-suffix"),F={1:"decimal",a:"lower-latin",A:"upper-latin",i:"lower-roman",I:"upper-roman"},v=v.getAttributeNS(m,"num-prefix")||"",v=F.hasOwnProperty(s)?v+(" counter(list, "+F[s]+")"):s?v+("'"+s+"';"):v+" ''";K&&(v+=" '"+K+"'");s="content: "+v+";";t(b,f,q,s)}else"list-level-style-image"===h.localName?(s="content: none;",t(b,f,q,s)):"list-level-style-bullet"===h.localName&&(s="content: '"+q.getAttributeNS(u,"bullet-char")+"';",t(b,f,q,s));h=h.nextSibling}else if("page"===c)if(K=q=f="",h=g.getElementsByTagNameNS(m,
"page-layout-properties")[0],q=h.parentNode.parentNode.parentNode.masterStyles,K="",f+=n(h,L),s=h.getElementsByTagNameNS(m,"background-image"),0<s.length&&(K=s.item(0).getAttributeNS(C,"href"))&&(f+="background-image: url('odfkit:"+K+"');",s=s.item(0),f+=n(s,E)),"presentation"===ga){if(q)for(s=q.getElementsByTagNameNS(m,"master-page"),F=0;F<s.length;F+=1)if(s[F].getAttributeNS(m,"page-layout-name")===h.parentNode.getAttributeNS(m,"name")){K=s[F].getAttributeNS(m,"name");q="draw|page[draw|master-page-name="+
K+"] {"+f+"}";K="office|body, draw|page[draw|master-page-name="+K+"] {"+n(h,ea)+" }";try{b.insertRule(q,b.cssRules.length),b.insertRule(K,b.cssRules.length)}catch(ja){throw ja;}}}else{if("text"===ga){q="office|text {"+f+"}";K="office|body {width: "+h.getAttributeNS(k,"page-width")+";}";try{b.insertRule(q,b.cssRules.length),b.insertRule(K,b.cssRules.length)}catch(fa){throw fa;}}}else{f=p(c,f,g).join(",");h="";if(q=a(g,m,"text-properties")){var F=q,W;s=W="";K=1;q=""+n(F,y);v=F.getAttributeNS(m,"text-underline-style");
"solid"===v&&(W+=" underline");v=F.getAttributeNS(m,"text-line-through-style");"solid"===v&&(W+=" line-through");W.length&&(q+="text-decoration:"+W+";");if(W=F.getAttributeNS(m,"font-name")||F.getAttributeNS(k,"font-family"))v=aa[W],q+="font-family: "+(v||W)+", sans-serif;";v=F.parentNode;if(F=e(v)){for(;v;){if(F=e(v)){if("%"!==F.unit){s="font-size: "+F.value*K+F.unit+";";break}K*=F.value/100}F=v;W=v="";v=null;"default-style"===F.localName?v=null:(v=F.getAttributeNS(m,"parent-style-name"),W=F.getAttributeNS(m,
"family"),v=U.getODFElementsWithXPath(P,v?"//style:*[@style:name='"+v+"'][@style:family='"+W+"']":"//style:default-style[@style:family='"+W+"']",odf.Namespaces.resolvePrefix)[0])}s||(s="font-size: "+parseFloat(X)*K+M.getUnits(X)+";");q+=s}h+=q}if(q=a(g,m,"paragraph-properties"))s=q,q=""+n(s,D),K=s.getElementsByTagNameNS(m,"background-image"),0<K.length&&(F=K.item(0).getAttributeNS(C,"href"))&&(q+="background-image: url('odfkit:"+F+"');",K=K.item(0),q+=n(K,E)),(s=s.getAttributeNS(k,"line-height"))&&
"normal"!==s&&(s=ba.parseFoLineHeight(s),q="%"!==s.unit?q+("line-height: "+s.value+s.unit+";"):q+("line-height: "+s.value/100+";")),h+=q;if(q=a(g,m,"graphic-properties"))F=q,q=""+n(F,N),s=F.getAttributeNS(r,"opacity"),K=F.getAttributeNS(r,"fill"),F=F.getAttributeNS(r,"fill-color"),"solid"===K||"hatch"===K?F&&"none"!==F?(s=isNaN(parseFloat(s))?1:parseFloat(s)/100,(F=d(F))&&(q+="background-color: rgba("+F.r+","+F.g+","+F.b+","+s+");")):q+="background: none;":"none"===K&&(q+="background: none;"),h+=
q;if(q=a(g,m,"drawing-page-properties"))s=""+n(q,N),"true"===q.getAttributeNS(x,"background-visible")&&(s+="background: none;"),h+=s;if(q=a(g,m,"table-cell-properties"))q=""+n(q,A),h+=q;if(q=a(g,m,"table-row-properties"))q=""+n(q,B),h+=q;if(q=a(g,m,"table-column-properties"))q=""+n(q,O),h+=q;if(q=a(g,m,"table-properties"))s=q,q=""+n(s,J),s=s.getAttributeNS(w,"border-model"),"collapsing"===s?q+="border-collapse:collapse;":"separating"===s&&(q+="border-collapse:separate;"),h+=q;if(0!==h.length)try{b.insertRule(f+
"{"+h+"}",b.cssRules.length)}catch(T){throw T;}}for(var ia in g.derivedStyles)g.derivedStyles.hasOwnProperty(ia)&&l(b,c,ia,g.derivedStyles[ia])}var r=odf.Namespaces.drawns,k=odf.Namespaces.fons,m=odf.Namespaces.stylens,q=odf.Namespaces.svgns,w=odf.Namespaces.tablens,u=odf.Namespaces.textns,C=odf.Namespaces.xlinkns,x=odf.Namespaces.presentationns,s={graphic:"draw","drawing-page":"draw",paragraph:"text",presentation:"presentation",ruby:"text",section:"text",table:"table","table-cell":"table","table-column":"table",
"table-row":"table",text:"text",list:"text",page:"office"},v={graphic:"circle connected control custom-shape ellipse frame g line measure page page-thumbnail path polygon polyline rect regular-polygon".split(" "),paragraph:"alphabetical-index-entry-template h illustration-index-entry-template index-source-style object-index-entry-template p table-index-entry-template table-of-content-entry-template user-index-entry-template".split(" "),presentation:"caption circle connector control custom-shape ellipse frame g line measure page-thumbnail path polygon polyline rect regular-polygon".split(" "),
"drawing-page":"caption circle connector control page custom-shape ellipse frame g line measure page-thumbnail path polygon polyline rect regular-polygon".split(" "),ruby:["ruby","ruby-text"],section:"alphabetical-index bibliography illustration-index index-title object-index section table-of-content table-index user-index".split(" "),table:["background","table"],"table-cell":"body covered-table-cell even-columns even-rows first-column first-row last-column last-row odd-columns odd-rows table-cell".split(" "),
"table-column":["table-column"],"table-row":["table-row"],text:"a index-entry-chapter index-entry-link-end index-entry-link-start index-entry-page-number index-entry-span index-entry-tab-stop index-entry-text index-title-template linenumbering-configuration list-level-style-number list-level-style-bullet outline-level-style span".split(" "),list:["list-item"]},y=[[k,"color","color"],[k,"background-color","background-color"],[k,"font-weight","font-weight"],[k,"font-style","font-style"]],E=[[m,"repeat",
"background-repeat"]],D=[[k,"background-color","background-color"],[k,"text-align","text-align"],[k,"text-indent","text-indent"],[k,"padding","padding"],[k,"padding-left","padding-left"],[k,"padding-right","padding-right"],[k,"padding-top","padding-top"],[k,"padding-bottom","padding-bottom"],[k,"border-left","border-left"],[k,"border-right","border-right"],[k,"border-top","border-top"],[k,"border-bottom","border-bottom"],[k,"margin","margin"],[k,"margin-left","margin-left"],[k,"margin-right","margin-right"],
[k,"margin-top","margin-top"],[k,"margin-bottom","margin-bottom"],[k,"border","border"]],N=[[k,"background-color","background-color"],[k,"min-height","min-height"],[r,"stroke","border"],[q,"stroke-color","border-color"],[q,"stroke-width","border-width"],[k,"border","border"],[k,"border-left","border-left"],[k,"border-right","border-right"],[k,"border-top","border-top"],[k,"border-bottom","border-bottom"]],A=[[k,"background-color","background-color"],[k,"border-left","border-left"],[k,"border-right",
"border-right"],[k,"border-top","border-top"],[k,"border-bottom","border-bottom"],[k,"border","border"]],O=[[m,"column-width","width"]],B=[[m,"row-height","height"],[k,"keep-together",null]],J=[[m,"width","width"],[k,"margin-left","margin-left"],[k,"margin-right","margin-right"],[k,"margin-top","margin-top"],[k,"margin-bottom","margin-bottom"]],L=[[k,"background-color","background-color"],[k,"padding","padding"],[k,"padding-left","padding-left"],[k,"padding-right","padding-right"],[k,"padding-top",
"padding-top"],[k,"padding-bottom","padding-bottom"],[k,"border","border"],[k,"border-left","border-left"],[k,"border-right","border-right"],[k,"border-top","border-top"],[k,"border-bottom","border-bottom"],[k,"margin","margin"],[k,"margin-left","margin-left"],[k,"margin-right","margin-right"],[k,"margin-top","margin-top"],[k,"margin-bottom","margin-bottom"]],ea=[[k,"page-width","width"],[k,"page-height","height"]],fa={border:!0,"border-left":!0,"border-right":!0,"border-top":!0,"border-bottom":!0,
"stroke-width":!0},aa={},ba=new odf.OdfUtils,ga,P,X,U=new xmldom.XPath,M=new core.CSSUnits;this.style2css=function(a,b,c,d,e){for(var k,h,q,m;b.cssRules.length;)b.deleteRule(b.cssRules.length-1);k=null;d&&(k=d.ownerDocument,P=d.parentNode);e&&(k=e.ownerDocument,P=e.parentNode);if(k)for(m in odf.Namespaces.forEachPrefix(function(a,c){q="@namespace "+a+" url("+c+");";try{b.insertRule(q,b.cssRules.length)}catch(d){}}),aa=c,ga=a,X=runtime.getWindow().getComputedStyle(document.body,null).getPropertyValue("font-size")||
"12pt",a=f(d),d=f(e),e={},s)if(s.hasOwnProperty(m))for(h in c=e[m]={},g(a[m],c),g(d[m],c),c)c.hasOwnProperty(h)&&l(b,m,h,c[h])}};
// Input 33
runtime.loadClass("core.Base64");runtime.loadClass("core.Zip");runtime.loadClass("xmldom.LSSerializer");runtime.loadClass("odf.StyleInfo");runtime.loadClass("odf.Namespaces");runtime.loadClass("odf.OdfNodeFilter");
odf.OdfContainer=function(){function f(a,b,c){for(a=a?a.firstChild:null;a;){if(a.localName===c&&a.namespaceURI===b)return a;a=a.nextSibling}return null}function h(a){var b,c=l.length;for(b=0;b<c;b+=1)if(a.namespaceURI===e&&a.localName===l[b])return b;return-1}function c(a,b){var c=new n.UsedStyleList(a,b),d=new odf.OdfNodeFilter;this.acceptNode=function(a){var e=d.acceptNode(a);e===NodeFilter.FILTER_ACCEPT&&(a.parentNode===b&&a.nodeType===Node.ELEMENT_NODE)&&(e=c.uses(a)?NodeFilter.FILTER_ACCEPT:
NodeFilter.FILTER_REJECT);return e}}function g(a,b){var d=new c(a,b);this.acceptNode=function(a){var b=d.acceptNode(a);b!==NodeFilter.FILTER_ACCEPT||(!a.parentNode||a.parentNode.namespaceURI!==odf.Namespaces.textns||"s"!==a.parentNode.localName&&"tab"!==a.parentNode.localName)||(b=NodeFilter.FILTER_REJECT);return b}}function b(a,b){if(b){var c=h(b),d,e=a.firstChild;if(-1!==c){for(;e;){d=h(e);if(-1!==d&&d>c)break;e=e.nextSibling}a.insertBefore(b,e)}}}function p(a){this.OdfContainer=a}function a(a,
b,c,d){var e=this;this.size=0;this.type=null;this.name=a;this.container=c;this.onchange=this.onreadystatechange=this.document=this.mimetype=this.url=null;this.EMPTY=0;this.LOADING=1;this.DONE=2;this.state=this.EMPTY;this.load=function(){null!==d&&(this.mimetype=b,d.loadAsDataURL(a,b,function(a,b){a&&runtime.log(a);e.url=b;if(e.onchange)e.onchange(e);if(e.onstatereadychange)e.onstatereadychange(e)}))}}var n=new odf.StyleInfo,e="urn:oasis:names:tc:opendocument:xmlns:office:1.0",d="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
t="urn:webodf:names:scope",l="meta settings scripts font-face-decls styles automatic-styles master-styles body".split(" "),r=(new Date).getTime()+"_webodf_",k=new core.Base64;p.prototype=new function(){};p.prototype.constructor=p;p.namespaceURI=e;p.localName="document";a.prototype.load=function(){};a.prototype.getUrl=function(){return this.data?"data:;base64,"+k.toBase64(this.data):null};odf.OdfContainer=function q(k,h){function l(a){for(var b=a.firstChild,c;b;)c=b.nextSibling,b.nodeType===Node.ELEMENT_NODE?
l(b):b.nodeType===Node.PROCESSING_INSTRUCTION_NODE&&a.removeChild(b),b=c}function x(a,b){for(var c=a&&a.firstChild;c;)c.nodeType===Node.ELEMENT_NODE&&c.setAttributeNS(t,"scope",b),c=c.nextSibling}function s(a,b){var c=null,d,e,f;if(a)for(c=a.cloneNode(!0),d=c.firstChild;d;)e=d.nextSibling,d.nodeType===Node.ELEMENT_NODE&&(f=d.getAttributeNS(t,"scope"))&&f!==b&&c.removeChild(d),d=e;return c}function v(a){var b=H.rootElement.ownerDocument,c;if(a){l(a.documentElement);try{c=b.importNode(a.documentElement,
!0)}catch(d){}}return c}function y(a){H.state=a;if(H.onchange)H.onchange(H);if(H.onstatereadychange)H.onstatereadychange(H)}function E(a){Z=null;H.rootElement=a;a.fontFaceDecls=f(a,e,"font-face-decls");a.styles=f(a,e,"styles");a.automaticStyles=f(a,e,"automatic-styles");a.masterStyles=f(a,e,"master-styles");a.body=f(a,e,"body");a.meta=f(a,e,"meta")}function D(a){a=v(a);var c=H.rootElement;a&&"document-styles"===a.localName&&a.namespaceURI===e?(c.fontFaceDecls=f(a,e,"font-face-decls"),b(c,c.fontFaceDecls),
c.styles=f(a,e,"styles"),b(c,c.styles),c.automaticStyles=f(a,e,"automatic-styles"),x(c.automaticStyles,"document-styles"),b(c,c.automaticStyles),c.masterStyles=f(a,e,"master-styles"),b(c,c.masterStyles),n.prefixStyleNames(c.automaticStyles,r,c.masterStyles)):y(q.INVALID)}function N(a){a=v(a);var c,d,g;if(a&&"document-content"===a.localName&&a.namespaceURI===e){c=H.rootElement;d=f(a,e,"font-face-decls");if(c.fontFaceDecls&&d)for(g=d.firstChild;g;)c.fontFaceDecls.appendChild(g),g=d.firstChild;else d&&
(c.fontFaceDecls=d,b(c,d));d=f(a,e,"automatic-styles");x(d,"document-content");if(c.automaticStyles&&d)for(g=d.firstChild;g;)c.automaticStyles.appendChild(g),g=d.firstChild;else d&&(c.automaticStyles=d,b(c,d));c.body=f(a,e,"body");b(c,c.body)}else y(q.INVALID)}function A(a){a=v(a);var c;a&&("document-meta"===a.localName&&a.namespaceURI===e)&&(c=H.rootElement,c.meta=f(a,e,"meta"),b(c,c.meta))}function O(a){a=v(a);var c;a&&("document-settings"===a.localName&&a.namespaceURI===e)&&(c=H.rootElement,c.settings=
f(a,e,"settings"),b(c,c.settings))}function B(a){a=v(a);var b;if(a&&"manifest"===a.localName&&a.namespaceURI===d)for(b=H.rootElement,b.manifest=a,a=b.manifest.firstChild;a;)a.nodeType===Node.ELEMENT_NODE&&("file-entry"===a.localName&&a.namespaceURI===d)&&(Q[a.getAttributeNS(d,"full-path")]=a.getAttributeNS(d,"media-type")),a=a.nextSibling}function J(a){var b=a.shift(),c,d;b?(c=b[0],d=b[1],R.loadAsDOM(c,function(b,c){d(c);b||H.state===q.INVALID||J(a)})):y(q.DONE)}function L(a){var b="";odf.Namespaces.forEachPrefix(function(a,
c){b+=" xmlns:"+a+'="'+c+'"'});return'<?xml version="1.0" encoding="UTF-8"?><office:'+a+" "+b+' office:version="1.2">'}function ea(){var a=new xmldom.LSSerializer,b=L("document-meta");a.filter=new odf.OdfNodeFilter;b+=a.writeToString(H.rootElement.meta,odf.Namespaces.namespaceMap);return b+"</office:document-meta>"}function fa(a,b){var c=document.createElementNS(d,"manifest:file-entry");c.setAttributeNS(d,"manifest:full-path",a);c.setAttributeNS(d,"manifest:media-type",b);return c}function aa(){var a=
runtime.parseXML('<manifest:manifest xmlns:manifest="'+d+'"></manifest:manifest>'),b=f(a,d,"manifest"),c=new xmldom.LSSerializer,e;for(e in Q)Q.hasOwnProperty(e)&&b.appendChild(fa(e,Q[e]));c.filter=new odf.OdfNodeFilter;return'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'+c.writeToString(a,odf.Namespaces.namespaceMap)}function ba(){var a=new xmldom.LSSerializer,b=L("document-settings");a.filter=new odf.OdfNodeFilter;b+=a.writeToString(H.rootElement.settings,odf.Namespaces.namespaceMap);
return b+"</office:document-settings>"}function ga(){var a=odf.Namespaces.namespaceMap,b=new xmldom.LSSerializer,d=s(H.rootElement.automaticStyles,"document-styles"),e=H.rootElement.masterStyles&&H.rootElement.masterStyles.cloneNode(!0),f=L("document-styles");n.removePrefixFromStyleNames(d,r,e);b.filter=new c(e,d);f+=b.writeToString(H.rootElement.fontFaceDecls,a);f+=b.writeToString(H.rootElement.styles,a);f+=b.writeToString(d,a);f+=b.writeToString(e,a);return f+"</office:document-styles>"}function P(){var a=
odf.Namespaces.namespaceMap,b=new xmldom.LSSerializer,c=s(H.rootElement.automaticStyles,"document-content"),d=L("document-content");b.filter=new g(H.rootElement.body,c);d+=b.writeToString(c,a);d+=b.writeToString(H.rootElement.body,a);return d+"</office:document-content>"}function X(a,b){runtime.loadXML(a,function(a,c){if(a)b(a);else{var d=v(c);d&&"document"===d.localName&&d.namespaceURI===e?(E(d),y(q.DONE)):y(q.INVALID)}})}function U(){function a(b,c){var f;c||(c=b);f=document.createElementNS(e,c);
d[b]=f;d.appendChild(f)}var b=new core.Zip("",null),c=runtime.byteArrayFromString("application/vnd.oasis.opendocument.text","utf8"),d=H.rootElement,f=document.createElementNS(e,"text");b.save("mimetype",c,!1,new Date);a("meta");a("settings");a("scripts");a("fontFaceDecls","font-face-decls");a("styles");a("automaticStyles","automatic-styles");a("masterStyles","master-styles");a("body");d.body.appendChild(f);y(q.DONE);return b}function M(){var a,b=new Date;a=runtime.byteArrayFromString(ba(),"utf8");
R.save("settings.xml",a,!0,b);a=runtime.byteArrayFromString(ea(),"utf8");R.save("meta.xml",a,!0,b);a=runtime.byteArrayFromString(ga(),"utf8");R.save("styles.xml",a,!0,b);a=runtime.byteArrayFromString(P(),"utf8");R.save("content.xml",a,!0,b);a=runtime.byteArrayFromString(aa(),"utf8");R.save("META-INF/manifest.xml",a,!0,b)}function G(a,b){M();R.writeAs(a,function(a){b(a)})}var H=this,R,Q={},Z;this.onstatereadychange=h;this.rootElement=this.state=this.onchange=null;this.setRootElement=E;this.getContentElement=
function(){var a;Z||(a=H.rootElement.body,Z=a.getElementsByTagNameNS(e,"text")[0]||a.getElementsByTagNameNS(e,"presentation")[0]||a.getElementsByTagNameNS(e,"spreadsheet")[0]);return Z};this.getDocumentType=function(){var a=H.getContentElement();return a&&a.localName};this.getPart=function(b){return new a(b,Q[b],H,R)};this.getPartData=function(a,b){R.load(a,b)};this.createByteArray=function(a,b){M();R.createByteArray(a,b)};this.saveAs=G;this.save=function(a){G(k,a)};this.getUrl=function(){return k};
this.state=q.LOADING;this.rootElement=function(a){var b=document.createElementNS(a.namespaceURI,a.localName),c;a=new a;for(c in a)a.hasOwnProperty(c)&&(b[c]=a[c]);return b}(p);R=k?new core.Zip(k,function(a,b){R=b;a?X(k,function(b){a&&(R.error=a+"\n"+b,y(q.INVALID))}):J([["styles.xml",D],["content.xml",N],["meta.xml",A],["settings.xml",O],["META-INF/manifest.xml",B]])}):U()};odf.OdfContainer.EMPTY=0;odf.OdfContainer.LOADING=1;odf.OdfContainer.DONE=2;odf.OdfContainer.INVALID=3;odf.OdfContainer.SAVING=
4;odf.OdfContainer.MODIFIED=5;odf.OdfContainer.getContainer=function(a){return new odf.OdfContainer(a,null)};return odf.OdfContainer}();
// Input 34
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.Base64");runtime.loadClass("xmldom.XPath");runtime.loadClass("odf.OdfContainer");
odf.FontLoader=function(){function f(g,b,h,a,n){var e,d=0,t;for(t in g)if(g.hasOwnProperty(t)){if(d===h){e=t;break}d+=1}e?b.getPartData(g[e].href,function(d,r){if(d)runtime.log(d);else{var k="@font-face { font-family: '"+(g[e].family||e)+"'; src: url(data:application/x-font-ttf;charset=binary;base64,"+c.convertUTF8ArrayToBase64(r)+') format("truetype"); }';try{a.insertRule(k,a.cssRules.length)}catch(m){runtime.log("Problem inserting rule in CSS: "+runtime.toJson(m)+"\nRule: "+k)}}f(g,b,h+1,a,n)}):
n&&n()}var h=new xmldom.XPath,c=new core.Base64;odf.FontLoader=function(){this.loadFonts=function(c,b){for(var p=c.rootElement.fontFaceDecls;b.cssRules.length;)b.deleteRule(b.cssRules.length-1);if(p){var a={},n,e,d,t;if(p)for(p=h.getODFElementsWithXPath(p,"style:font-face[svg:font-face-src]",odf.Namespaces.resolvePrefix),n=0;n<p.length;n+=1)e=p[n],d=e.getAttributeNS(odf.Namespaces.stylens,"name"),t=e.getAttributeNS(odf.Namespaces.svgns,"font-family"),e=h.getODFElementsWithXPath(e,"svg:font-face-src/svg:font-face-uri",
odf.Namespaces.resolvePrefix),0<e.length&&(e=e[0].getAttributeNS(odf.Namespaces.xlinkns,"href"),a[d]={href:e,family:t});f(a,c,0,b)}}};return odf.FontLoader}();
// Input 35
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.Utils");runtime.loadClass("odf.Namespaces");runtime.loadClass("odf.OdfContainer");runtime.loadClass("odf.StyleInfo");runtime.loadClass("odf.OdfUtils");runtime.loadClass("odf.TextStyleApplicator");
odf.Formatting=function(){function f(a,b){Object.keys(b).forEach(function(c){try{a[c]=b[c].constructor===Object?f(a[c],b[c]):b[c]}catch(d){a[c]=b[c]}});return a}function h(a,b,c){var e,f;c=c||[d.rootElement.automaticStyles,d.rootElement.styles];for(e=c.shift();e;){for(e=e.firstChild;e;){if(e.nodeType===Node.ELEMENT_NODE&&(f=e.getAttributeNS(r,"name"),e.namespaceURI===r&&"style"===e.localName&&e.getAttributeNS(r,"family")===b&&f===a||"list-style"===b&&e.namespaceURI===k&&"list-style"===e.localName&&
f===a||"data"===b&&e.namespaceURI===m&&f===a))return e;e=e.nextSibling}e=c.shift()}return null}function c(a){for(var b={},c=a.firstChild;c;){if(c.nodeType===Node.ELEMENT_NODE&&c.namespaceURI===r)for(b[c.nodeName]={},a=0;a<c.attributes.length;a+=1)b[c.nodeName][c.attributes[a].name]=c.attributes[a].value;c=c.nextSibling}return b}function g(a,b){Object.keys(b).forEach(function(c){var d=c.split(":"),e=d[1],f=odf.Namespaces.resolvePrefix(d[0]),d=b[c];"object"===typeof d&&Object.keys(d).length?(c=a.getElementsByTagNameNS(f,
e)[0]||a.ownerDocument.createElementNS(f,c),a.appendChild(c),g(c,d)):a.setAttributeNS(f,c,d)})}function b(a){var b=d.rootElement.styles,e;e={};for(var g={},k=a;k;)e=c(k),g=f(e,g),k=(e=k.getAttributeNS(r,"parent-style-name"))?h(e,a.getAttributeNS(r,"family"),[b]):null;a:{a=a.getAttributeNS(r,"family");for(b=d.rootElement.styles.firstChild;b;){if(b.nodeType===Node.ELEMENT_NODE&&b.namespaceURI===r&&"default-style"===b.localName&&b.getAttributeNS(r,"family")===a){k=b;break a}b=b.nextSibling}k=null}k&&
(e=c(k),g=f(e,g));return g}function p(a,b){for(var c=a.nodeType===Node.TEXT_NODE?a.parentNode:a,d,e=[],f="",g=!1;c;)!g&&q.isGroupingElement(c)&&(g=!0),(d=t.determineStylesForNode(c))&&e.push(d),c=c.parentNode;g&&(e.forEach(function(a){Object.keys(a).forEach(function(b){Object.keys(a[b]).forEach(function(a){f+="|"+b+":"+a+"|"})})}),b&&(b[f]=e));return g?e:void 0}function a(a){var c={orderedStyles:[]};a.forEach(function(a){Object.keys(a).forEach(function(d){var e=Object.keys(a[d])[0],g,k;(g=h(e,d))?
(k=b(g),c=f(k,c),k=g.getAttributeNS(r,"display-name")):runtime.log("No style element found for '"+e+"' of family '"+d+"'");c.orderedStyles.push({name:e,family:d,displayName:k})})});return c}function n(){var a,b=[];[d.rootElement.automaticStyles,d.rootElement.styles].forEach(function(c){for(a=c.firstChild;a;)a.nodeType===Node.ELEMENT_NODE&&(a.namespaceURI===r&&"style"===a.localName||a.namespaceURI===k&&"list-style"===a.localName)&&b.push(a.getAttributeNS(r,"name")),a=a.nextSibling});return b}var e=
this,d,t=new odf.StyleInfo,l=odf.Namespaces.svgns,r=odf.Namespaces.stylens,k=odf.Namespaces.textns,m=odf.Namespaces.numberns,q=new odf.OdfUtils,w=new core.Utils;this.setOdfContainer=function(a){d=a};this.getFontMap=function(){for(var a=d.rootElement.fontFaceDecls,b={},c,e,a=a&&a.firstChild;a;)a.nodeType===Node.ELEMENT_NODE&&(c=a.getAttributeNS(r,"name"))&&((e=a.getAttributeNS(l,"font-family"))||a.getElementsByTagNameNS(l,"font-face-uri")[0])&&(b[c]=e),a=a.nextSibling;return b};this.getAvailableParagraphStyles=
function(){for(var a=d.rootElement.styles&&d.rootElement.styles.firstChild,b,c,e=[];a;)a.nodeType===Node.ELEMENT_NODE&&("style"===a.localName&&a.namespaceURI===r)&&(c=a,b=c.getAttributeNS(r,"family"),"paragraph"===b&&(b=c.getAttributeNS(r,"name"),c=c.getAttributeNS(r,"display-name")||b,b&&c&&e.push({name:b,displayName:c}))),a=a.nextSibling;return e};this.isStyleUsed=function(a){var b;b=t.hasDerivedStyles(d.rootElement,odf.Namespaces.resolvePrefix,a);a=(new t.UsedStyleList(d.rootElement.styles)).uses(a)||
(new t.UsedStyleList(d.rootElement.automaticStyles)).uses(a)||(new t.UsedStyleList(d.rootElement.body)).uses(a);return b||a};this.getStyleElement=h;this.getStyleAttributes=c;this.getInheritedStyleAttributes=b;this.getFirstNamedParentStyleNameOrSelf=function(a){var b=d.rootElement.automaticStyles,c=d.rootElement.styles,e;for(e=h(a,"paragraph",[b]);e;)a=e.getAttributeNS(r,"parent-style-name"),e=h(a,"paragraph",[b]);return(e=h(a,"paragraph",[c]))?a:null};this.hasParagraphStyle=function(a){return Boolean(h(a,
"paragraph"))};this.getAppliedStyles=function(b){var c={},d=[];b.forEach(function(a){p(a,c)});Object.keys(c).forEach(function(b){d.push(a(c[b]))});return d};this.getAppliedStylesForElement=function(b){return(b=p(b))?a(b):void 0};this.applyStyle=function(a,b,c,f){(new odf.TextStyleApplicator("auto"+w.hashString(a)+"_",e,d.rootElement.automaticStyles)).applyStyle(b,c,f)};this.updateStyle=function(a,b,c){var d,e;g(a,b);if(c){a.getAttributeNS(r,"name");d=n();e=0;do b=c+e,e+=1;while(-1!==d.indexOf(b));
a.setAttributeNS(r,"style:name",b)}}};
// Input 36
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.DomUtils");runtime.loadClass("odf.OdfContainer");runtime.loadClass("odf.Formatting");runtime.loadClass("xmldom.XPath");runtime.loadClass("odf.FontLoader");runtime.loadClass("odf.Style2CSS");runtime.loadClass("odf.OdfUtils");runtime.loadClass("gui.AnnotationViewManager");
odf.OdfCanvas=function(){function f(){function a(d){c=!0;runtime.setTimeout(function(){try{d()}catch(e){runtime.log(e)}c=!1;0<b.length&&a(b.pop())},10)}var b=[],c=!1;this.clearQueue=function(){b.length=0};this.addToQueue=function(d){if(0===b.length&&!c)return a(d);b.push(d)}}function h(a){function b(){for(;0<c.cssRules.length;)c.deleteRule(0);c.insertRule("#shadowContent draw|page {display:none;}",0);c.insertRule("office|presentation draw|page {display:none;}",1);c.insertRule("#shadowContent draw|page:nth-of-type("+
d+") {display:block;}",2);c.insertRule("office|presentation draw|page:nth-of-type("+d+") {display:block;}",3)}var c=a.sheet,d=1;this.showFirstPage=function(){d=1;b()};this.showNextPage=function(){d+=1;b()};this.showPreviousPage=function(){1<d&&(d-=1,b())};this.showPage=function(a){0<a&&(d=a,b())};this.css=a}function c(a,b,c){a.addEventListener?a.addEventListener(b,c,!1):a.attachEvent?a.attachEvent("on"+b,c):a["on"+b]=c}function g(a){function b(a,c){for(;c;){if(c===a)return!0;c=c.parentNode}return!1}
function d(){var c=[],g=runtime.getWindow().getSelection(),k,h;for(k=0;k<g.rangeCount;k+=1)h=g.getRangeAt(k),null!==h&&(b(a,h.startContainer)&&b(a,h.endContainer))&&c.push(h);if(c.length===e.length){for(g=0;g<c.length&&(k=c[g],h=e[g],k=k===h?!1:null===k||null===h?!0:k.startContainer!==h.startContainer||k.startOffset!==h.startOffset||k.endContainer!==h.endContainer||k.endOffset!==h.endOffset,!k);g+=1);if(g===c.length)return}e=c;var g=[c.length],l,q=a.ownerDocument;for(k=0;k<c.length;k+=1)h=c[k],l=
q.createRange(),l.setStart(h.startContainer,h.startOffset),l.setEnd(h.endContainer,h.endOffset),g[k]=l;e=g;g=f.length;for(c=0;c<g;c+=1)f[c](a,e)}var e=[],f=[];this.addListener=function(a,b){var c,d=f.length;for(c=0;c<d;c+=1)if(f[c]===b)return;f.push(b)};c(a,"mouseup",d);c(a,"keyup",d);c(a,"keydown",d)}function b(a,b,c){(new odf.Style2CSS).style2css(a.getDocumentType(),c.sheet,b.getFontMap(),a.rootElement.styles,a.rootElement.automaticStyles)}function p(a,b,c,d){c.setAttribute("styleid",b);var e,f=
c.getAttributeNS(v,"anchor-type"),g=c.getAttributeNS(x,"x"),k=c.getAttributeNS(x,"y"),h=c.getAttributeNS(x,"width"),l=c.getAttributeNS(x,"height"),m=c.getAttributeNS(w,"min-height"),n=c.getAttributeNS(w,"min-width"),r=c.getAttributeNS(q,"master-page-name"),s=null,t,u;t=0;var A,y=a.rootElement.ownerDocument;if(r){s=a.rootElement.masterStyles.getElementsByTagNameNS(C,"master-page");t=null;for(u=0;u<s.length;u+=1)if(s[u].getAttributeNS(C,"name")===r){t=s[u];break}s=t}else s=null;if(s){r=y.createElementNS(q,
"draw:page");A=s.firstElementChild;for(t=0;A;)"true"!==A.getAttributeNS(D,"placeholder")&&(u=A.cloneNode(!0),r.appendChild(u),p(a,b+"_"+t,u,d)),A=A.nextElementSibling,t+=1;J.appendChild(r);t=J.getElementsByTagNameNS(q,"page").length;if(u=r.getElementsByTagNameNS(v,"page-number")[0]){for(;u.firstChild;)u.removeChild(u.firstChild);u.appendChild(y.createTextNode(t))}p(a,b,r,d);r.setAttributeNS(q,"draw:master-page-name",s.getAttributeNS(C,"name"))}if("as-char"===f)e="display: inline-block;";else if(f||
g||k)e="position: absolute;";else if(h||l||m||n)e="display: block;";g&&(e+="left: "+g+";");k&&(e+="top: "+k+";");h&&(e+="width: "+h+";");l&&(e+="height: "+l+";");m&&(e+="min-height: "+m+";");n&&(e+="min-width: "+n+";");e&&(e="draw|"+c.localName+'[styleid="'+b+'"] {'+e+"}",d.insertRule(e,d.cssRules.length))}function a(a){for(a=a.firstChild;a;){if(a.namespaceURI===u&&"binary-data"===a.localName)return"data:image/png;base64,"+a.textContent.replace(/[\r\n\s]/g,"");a=a.nextSibling}return""}function n(b,
c,d,e){function f(a){a&&(a='draw|image[styleid="'+b+'"] {'+("background-image: url("+a+");")+"}",e.insertRule(a,e.cssRules.length))}d.setAttribute("styleid",b);var g=d.getAttributeNS(y,"href"),k;if(g)try{k=c.getPart(g),k.onchange=function(a){f(a.url)},k.load()}catch(h){runtime.log("slight problem: "+h)}else g=a(d),f(g)}function e(a){function b(a){return d===a.getAttributeNS(u,"name")}var c=B.getElementsByTagNameNS(a,u,"annotation");a=B.getElementsByTagNameNS(a,u,"annotation-end");var d,e;for(e=0;e<
c.length;e+=1)d=c[e].getAttributeNS(u,"name"),aa.addAnnotation({node:c[e],end:a.filter(b)[0]||null});aa.rerenderAnnotations()}function d(a){function b(c){var d,e;c.hasAttributeNS(y,"href")&&(d=c.getAttributeNS(y,"href"),"#"===d[0]?(d=d.substring(1),e=function(){var b=A.getODFElementsWithXPath(a,"//text:bookmark-start[@text:name='"+d+"']",odf.Namespaces.resolvePrefix);0===b.length&&(b=A.getODFElementsWithXPath(a,"//text:bookmark[@text:name='"+d+"']",odf.Namespaces.resolvePrefix));0<b.length&&b[0].scrollIntoView(!0);
return!1}):e=function(){N.open(d)},c.onclick=e)}var c,d,e;d=a.getElementsByTagNameNS(v,"a");for(c=0;c<d.length;c+=1)e=d.item(c),b(e)}function t(a){var b=a.ownerDocument;B.getElementsByTagNameNS(a,v,"s").forEach(function(a){for(var c,d;a.firstChild;)a.removeChild(a.firstChild);a.appendChild(b.createTextNode(" "));d=parseInt(a.getAttributeNS(v,"c"),10);if(1<d)for(a.removeAttributeNS(v,"c"),c=1;c<d;c+=1)a.parentNode.insertBefore(a.cloneNode(!0),a)})}function l(a){B.getElementsByTagNameNS(a,v,"tab").forEach(function(a){a.textContent=
"\t"})}function r(b,c){function d(a,b){var g=k.documentElement.namespaceURI;"video/"===b.substr(0,6)?(e=k.createElementNS(g,"video"),e.setAttribute("controls","controls"),f=k.createElementNS(g,"source"),f.setAttribute("src",a),f.setAttribute("type",b),e.appendChild(f),c.parentNode.appendChild(e)):c.innerHtml="Unrecognised Plugin"}var e,f,g,k=c.ownerDocument,h;if(g=c.getAttributeNS(y,"href"))try{h=b.getPart(g),h.onchange=function(a){d(a.url,a.mimetype)},h.load()}catch(l){runtime.log("slight problem: "+
l)}else runtime.log("using MP4 data fallback"),g=a(c),d(g,"video/mp4")}function k(a){var b=a.getElementsByTagName("head")[0],c;"undefined"!==String(typeof webodf_css)?(c=a.createElementNS(b.namespaceURI,"style"),c.setAttribute("media","screen, print, handheld, projection"),c.appendChild(a.createTextNode(webodf_css))):(c=a.createElementNS(b.namespaceURI,"link"),a="webodf.css",runtime.currentDirectory&&(a=runtime.currentDirectory()+"/../"+a),c.setAttribute("href",a),c.setAttribute("rel","stylesheet"));
c.setAttribute("type","text/css");b.appendChild(c);return c}function m(a){var b=a.getElementsByTagName("head")[0],c=a.createElementNS(b.namespaceURI,"style"),d="";c.setAttribute("type","text/css");c.setAttribute("media","screen, print, handheld, projection");odf.Namespaces.forEachPrefix(function(a,b){d+="@namespace "+a+" url("+b+");\n"});c.appendChild(a.createTextNode(d));b.appendChild(c);return c}var q=odf.Namespaces.drawns,w=odf.Namespaces.fons,u=odf.Namespaces.officens,C=odf.Namespaces.stylens,
x=odf.Namespaces.svgns,s=odf.Namespaces.tablens,v=odf.Namespaces.textns,y=odf.Namespaces.xlinkns,E=odf.Namespaces.xmlns,D=odf.Namespaces.presentationns,N=runtime.getWindow(),A=new xmldom.XPath,O=new odf.OdfUtils,B=new core.DomUtils,J,L,ea,fa=!1,aa;odf.OdfCanvas=function(a){function u(a,b,c){function d(a,b,c,e){la.addToQueue(function(){n(a,b,c,e)})}var e,f;e=b.getElementsByTagNameNS(q,"image");for(b=0;b<e.length;b+=1)f=e.item(b),d("image"+String(b),a,f,c)}function w(a,b){function c(a,b){la.addToQueue(function(){r(a,
b)})}var d,e,f;e=b.getElementsByTagNameNS(q,"plugin");for(d=0;d<e.length;d+=1)f=e.item(d),c(a,f)}function x(){L.firstChild&&(1<T?(L.style.MozTransformOrigin="center top",L.style.WebkitTransformOrigin="center top",L.style.OTransformOrigin="center top",L.style.msTransformOrigin="center top"):(L.style.MozTransformOrigin="left top",L.style.WebkitTransformOrigin="left top",L.style.OTransformOrigin="left top",L.style.msTransformOrigin="left top"),L.style.WebkitTransform="scale("+T+")",L.style.MozTransform=
"scale("+T+")",L.style.OTransform="scale("+T+")",L.style.msTransform="scale("+T+")",a.style.width=Math.round(T*L.offsetWidth)+"px",a.style.height=Math.round(T*L.offsetHeight)+"px")}function D(a){fa?(ea.parentNode||(L.appendChild(ea),x()),aa&&aa.forgetAnnotations(),aa=new gui.AnnotationViewManager(Q,a.body,ea),e(a.body)):ea.parentNode&&(L.removeChild(ea),aa.forgetAnnotations(),x())}function y(c){function e(){for(var f=a;f.firstChild;)f.removeChild(f.firstChild);a.style.display="inline-block";f=$.rootElement;
a.ownerDocument.importNode(f,!0);ha.setOdfContainer($);var g=$,k=F;(new odf.FontLoader).loadFonts(g,k.sheet);b($,ha,ja);for(var k=$,g=oa.sheet,h=a;h.firstChild;)h.removeChild(h.firstChild);L=Z.createElementNS(a.namespaceURI,"div");L.style.display="inline-block";L.style.background="white";L.appendChild(f);a.appendChild(L);ea=Z.createElementNS(a.namespaceURI,"div");ea.id="annotationsPane";J=Z.createElementNS(a.namespaceURI,"div");J.id="shadowContent";J.style.position="absolute";J.style.top=0;J.style.left=
0;k.getContentElement().appendChild(J);var h=f.body,m,n,r;n=[];for(m=h.firstChild;m&&m!==h;)if(m.namespaceURI===q&&(n[n.length]=m),m.firstChild)m=m.firstChild;else{for(;m&&m!==h&&!m.nextSibling;)m=m.parentNode;m&&m.nextSibling&&(m=m.nextSibling)}for(r=0;r<n.length;r+=1)m=n[r],p(k,"frame"+String(r),m,g);n=A.getODFElementsWithXPath(h,".//*[*[@text:anchor-type='paragraph']]",odf.Namespaces.resolvePrefix);for(m=0;m<n.length;m+=1)h=n[m],h.setAttributeNS&&h.setAttributeNS("urn:webodf","containsparagraphanchor",
!0);m=f.body.getElementsByTagNameNS(s,"table-cell");for(h=0;h<m.length;h+=1)n=m.item(h),n.hasAttributeNS(s,"number-columns-spanned")&&n.setAttribute("colspan",n.getAttributeNS(s,"number-columns-spanned")),n.hasAttributeNS(s,"number-rows-spanned")&&n.setAttribute("rowspan",n.getAttributeNS(s,"number-rows-spanned"));d(f.body);t(f.body);l(f.body);u(k,f.body,g);w(k,f.body);n=f.body;var y,z,B,V,h={};m={};var S;r=N.document.getElementsByTagNameNS(v,"list-style");for(k=0;k<r.length;k+=1)y=r.item(k),(B=y.getAttributeNS(C,
"name"))&&(m[B]=y);n=n.getElementsByTagNameNS(v,"list");for(k=0;k<n.length;k+=1)if(y=n.item(k),r=y.getAttributeNS(E,"id")){z=y.getAttributeNS(v,"continue-list");y.setAttribute("id",r);V="text|list#"+r+" > text|list-item > *:first-child:before {";if(B=y.getAttributeNS(v,"style-name")){y=m[B];S=O.getFirstNonWhitespaceChild(y);y=void 0;if(S)if("list-level-style-number"===S.localName){y=S.getAttributeNS(C,"num-format");B=S.getAttributeNS(C,"num-suffix");var va="",va={1:"decimal",a:"lower-latin",A:"upper-latin",
i:"lower-roman",I:"upper-roman"},qa=void 0,qa=S.getAttributeNS(C,"num-prefix")||"",qa=va.hasOwnProperty(y)?qa+(" counter(list, "+va[y]+")"):y?qa+("'"+y+"';"):qa+" ''";B&&(qa+=" '"+B+"'");y=va="content: "+qa+";"}else"list-level-style-image"===S.localName?y="content: none;":"list-level-style-bullet"===S.localName&&(y="content: '"+S.getAttributeNS(v,"bullet-char")+"';");S=y}if(z){for(y=h[z];y;)z=y,y=h[z];V+="counter-increment:"+z+";";S?(S=S.replace("list",z),V+=S):V+="content:counter("+z+");"}else z=
"",S?(S=S.replace("list",r),V+=S):V+="content: counter("+r+");",V+="counter-increment:"+r+";",g.insertRule("text|list#"+r+" {counter-reset:"+r+"}",g.cssRules.length);V+="}";h[r]=z;V&&g.insertRule(V,g.cssRules.length)}L.insertBefore(J,L.firstChild);x();D(f);if(!c&&(f=[$],ia.hasOwnProperty("statereadychange")))for(g=ia.statereadychange,S=0;S<g.length;S+=1)g[S].apply(null,f)}$.state===odf.OdfContainer.DONE?e():(runtime.log("WARNING: refreshOdf called but ODF was not DONE."),runtime.setTimeout(function sa(){$.state===
odf.OdfContainer.DONE?e():(runtime.log("will be back later..."),runtime.setTimeout(sa,500))},100))}function B(b){la.clearQueue();a.innerHTML="loading "+b;a.removeAttribute("style");$=new odf.OdfContainer(b,function(a){$=a;y(!1)})}function H(){if(Y){for(var a=Y.ownerDocument.createDocumentFragment();Y.firstChild;)a.insertBefore(Y.firstChild,null);Y.parentNode.replaceChild(a,Y)}}function R(a){a=a||N.event;for(var b=a.target,c=N.getSelection(),d=0<c.rangeCount?c.getRangeAt(0):null,e=d&&d.startContainer,
f=d&&d.startOffset,g=d&&d.endContainer,k=d&&d.endOffset,h,l;b&&("p"!==b.localName&&"h"!==b.localName||b.namespaceURI!==v);)b=b.parentNode;W&&(b&&b.parentNode!==Y)&&(h=b.ownerDocument,l=h.documentElement.namespaceURI,Y?Y.parentNode&&H():(Y=h.createElementNS(l,"p"),Y.style.margin="0px",Y.style.padding="0px",Y.style.border="0px",Y.setAttribute("contenteditable",!0)),b.parentNode.replaceChild(Y,b),Y.appendChild(b),Y.focus(),d&&(c.removeAllRanges(),d=b.ownerDocument.createRange(),d.setStart(e,f),d.setEnd(g,
k),c.addRange(d)),a.preventDefault?(a.preventDefault(),a.stopPropagation()):(a.returnValue=!1,a.cancelBubble=!0))}runtime.assert(null!==a&&void 0!==a,"odf.OdfCanvas constructor needs DOM element");runtime.assert(null!==a.ownerDocument&&void 0!==a.ownerDocument,"odf.OdfCanvas constructor needs DOM");var Q=this,Z=a.ownerDocument,$,ha=new odf.Formatting,na=new g(a),K,F,ja,oa,W=!1,T=1,ia={},Y,la=new f;k(Z);K=new h(m(Z));F=m(Z);ja=m(Z);oa=m(Z);this.refreshCSS=function(){b($,ha,ja);x()};this.refreshSize=
function(){x()};this.odfContainer=function(){return $};this.slidevisibilitycss=function(){return K.css};this.setOdfContainer=function(a,b){$=a;y(!0===b)};this.load=this.load=B;this.save=function(a){H();$.save(a)};this.setEditable=function(b){c(a,"click",R);(W=b)||H()};this.addListener=function(b,d){switch(b){case "selectionchange":na.addListener(b,d);break;case "click":c(a,b,d);break;default:var e=ia[b];void 0===e&&(e=ia[b]=[]);d&&-1===e.indexOf(d)&&e.push(d)}};this.getFormatting=function(){return ha};
this.getAnnotationManager=function(){return aa};this.refreshAnnotations=function(){D($.rootElement)};this.rerenderAnnotations=function(){aa&&aa.rerenderAnnotations()};this.getSizer=function(){return L};this.enableAnnotations=function(a){a!==fa&&(fa=a,D($.rootElement))};this.addAnnotation=function(a){aa&&aa.addAnnotation(a)};this.forgetAnnotations=function(){aa&&aa.forgetAnnotations()};this.setZoomLevel=function(a){T=a;x()};this.getZoomLevel=function(){return T};this.fitToContainingElement=function(b,
c){var d=a.offsetHeight/T;T=b/(a.offsetWidth/T);c/d<T&&(T=c/d);x()};this.fitToWidth=function(b){T=b/(a.offsetWidth/T);x()};this.fitSmart=function(b,c){var d,e;d=a.offsetWidth/T;e=a.offsetHeight/T;d=b/d;void 0!==c&&c/e<d&&(d=c/e);T=Math.min(1,d);x()};this.fitToHeight=function(b){T=b/(a.offsetHeight/T);x()};this.showFirstPage=function(){K.showFirstPage()};this.showNextPage=function(){K.showNextPage()};this.showPreviousPage=function(){K.showPreviousPage()};this.showPage=function(a){K.showPage(a);x()};
this.getElement=function(){return a}};return odf.OdfCanvas}();
// Input 37
runtime.loadClass("odf.OdfCanvas");
odf.CommandLineTools=function(){this.roundTrip=function(f,h,c){return new odf.OdfContainer(f,function(g){if(g.state===odf.OdfContainer.INVALID)return c("Document "+f+" is invalid.");g.state===odf.OdfContainer.DONE?g.saveAs(h,function(b){c(b)}):c("Document was not completely loaded.")})};this.render=function(f,h,c){for(h=h.getElementsByTagName("body")[0];h.firstChild;)h.removeChild(h.firstChild);h=new odf.OdfCanvas(h);h.addListener("statereadychange",function(f){c(f)});h.load(f)}};
// Input 38
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.Server=function(){};ops.Server.prototype.connect=function(f,h){};ops.Server.prototype.networkStatus=function(){};ops.Server.prototype.login=function(f,h,c,g){};ops.Server.prototype.joinSession=function(f,h,c,g){};ops.Server.prototype.getGenesisUrl=function(f){};
// Input 39
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.Operation=function(){};ops.Operation.prototype.init=function(f){};ops.Operation.prototype.execute=function(f){};ops.Operation.prototype.spec=function(){};
// Input 40
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpAddCursor=function(){var f,h;this.init=function(c){f=c.memberid;h=c.timestamp};this.execute=function(c){var g=c.getCursor(f);if(g)return!1;g=new ops.OdtCursor(f,c);c.addCursor(g);c.emit(ops.OdtDocument.signalCursorAdded,g);return!0};this.spec=function(){return{optype:"AddCursor",memberid:f,timestamp:h}}};
// Input 41
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.DomUtils");runtime.loadClass("odf.OdfUtils");
gui.StyleHelper=function(f){function h(b,c,a){var h=!0,e;b.collapsed?(e=b.startContainer,e.hasChildNodes()&&b.startOffset<e.childNodes.length&&(e=e.childNodes[b.startOffset]),b=[e]):b=g.getTextNodes(b,!0);b=f.getAppliedStyles(b);for(e=0;e<b.length&&!(h=b[e]["style:text-properties"],h=!h||h[c]!==a);e+=1);return!h}var c=new core.DomUtils,g=new odf.OdfUtils;this.getAppliedStyles=function(b){b=g.getTextNodes(b,!0);return f.getAppliedStyles(b)};this.applyStyle=function(b,h,a){var n=c.splitBoundaries(h),
e=g.getTextNodes(h,!1);f.applyStyle(b,e,{startContainer:h.startContainer,startOffset:h.startOffset,endContainer:h.endContainer,endOffset:h.endOffset},a);n.forEach(c.normalizeTextNodes)};this.isBold=function(b){return h(b,"fo:font-weight","bold")};this.isItalic=function(b){return h(b,"fo:font-style","italic")};this.hasUnderline=function(b){return h(b,"style:text-underline-style","solid")};this.hasStrikeThrough=function(b){return h(b,"style:text-line-through-style","solid")}};
// Input 42
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("gui.StyleHelper");runtime.loadClass("odf.OdfUtils");
ops.OpApplyDirectStyling=function(){function f(a){var c=0<=b?g+b:g,d=a.getIteratorAtPosition(0<=b?g:g+b),c=b?a.getIteratorAtPosition(c):d;a=a.getDOM().createRange();a.setStart(d.container(),d.unfilteredDomOffset());a.setEnd(c.container(),c.unfilteredDomOffset());return a}var h,c,g,b,p,a=new odf.OdfUtils;this.init=function(a){h=a.memberid;c=a.timestamp;g=parseInt(a.position,10);b=parseInt(a.length,10);p=a.setProperties};this.execute=function(b){var e=f(b),d=a.getImpactedParagraphs(e);(new gui.StyleHelper(b.getFormatting())).applyStyle(h,
e,p);e.detach();b.getOdfCanvas().refreshCSS();d.forEach(function(a){b.emit(ops.OdtDocument.signalParagraphChanged,{paragraphElement:a,memberId:h,timeStamp:c})});b.getOdfCanvas().rerenderAnnotations();return!0};this.spec=function(){return{optype:"ApplyDirectStyling",memberid:h,timestamp:c,position:g,length:b,setProperties:p}}};
// Input 43
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpRemoveCursor=function(){var f,h;this.init=function(c){f=c.memberid;h=c.timestamp};this.execute=function(c){return c.removeCursor(f)?!0:!1};this.spec=function(){return{optype:"RemoveCursor",memberid:f,timestamp:h}}};
// Input 44
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpMoveCursor=function(){var f,h,c,g;this.init=function(b){f=b.memberid;h=b.timestamp;c=b.position;g=b.length||0};this.execute=function(b){var h=b.getCursor(f),a=b.getCursorPosition(f),n=b.getPositionFilter(),e=c-a;if(!h)return!1;a=h.getStepCounter();e=0<e?a.countForwardSteps(e,n):0>e?-a.countBackwardSteps(-e,n):0;h.move(e);g&&(n=0<g?a.countForwardSteps(g,n):0>g?-a.countBackwardSteps(-g,n):0,h.move(n,!0));b.emit(ops.OdtDocument.signalCursorMoved,h);return!0};this.spec=function(){return{optype:"MoveCursor",
memberid:f,timestamp:h,position:c,length:g}}};
// Input 45
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpInsertTable=function(){function f(a,c){var e;if(1===d.length)e=d[0];else if(3===d.length)switch(a){case 0:e=d[0];break;case g-1:e=d[2];break;default:e=d[1]}else e=d[a];if(1===e.length)return e[0];if(3===e.length)switch(c){case 0:return e[0];case b-1:return e[2];default:return e[1]}return e[c]}var h,c,g,b,p,a,n,e,d;this.init=function(f){h=f.memberid;c=f.timestamp;p=f.position;g=f.initialRows;b=f.initialColumns;a=f.tableName;n=f.tableStyleName;e=f.tableColumnStyleName;d=f.tableCellStyleMatrix};
this.execute=function(d){var l=d.getPositionInTextNode(p),r=d.getRootNode();if(l){var k=d.getDOM(),m=k.createElementNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:table"),q=k.createElementNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:table-column"),w,u,C,x;n&&m.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:style-name",n);a&&m.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:name",a);q.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0",
"table:number-columns-repeated",b);e&&q.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:style-name",e);m.appendChild(q);for(C=0;C<g;C+=1){q=k.createElementNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:table-row");for(x=0;x<b;x+=1)w=k.createElementNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:table-cell"),(u=f(C,x))&&w.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:table:1.0","table:style-name",u),u=k.createElementNS("urn:oasis:names:tc:opendocument:xmlns:text:1.0",
"text:p"),w.appendChild(u),q.appendChild(w);m.appendChild(q)}l=d.getParagraphElement(l.textNode);r.insertBefore(m,l?l.nextSibling:void 0);d.getOdfCanvas().refreshSize();d.emit(ops.OdtDocument.signalTableAdded,{tableElement:m,memberId:h,timeStamp:c});d.getOdfCanvas().rerenderAnnotations();return!0}return!1};this.spec=function(){return{optype:"InsertTable",memberid:h,timestamp:c,position:p,initialRows:g,initialColumns:b,tableName:a,tableStyleName:n,tableColumnStyleName:e,tableCellStyleMatrix:d}}};
// Input 46
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpInsertText=function(){function f(b,a){var c=a.parentNode,e=a.nextSibling,d=[];b.getCursors().forEach(function(b){var c=b.getSelectedRange();!c||c.startContainer!==a&&c.endContainer!==a||d.push({cursor:b,startContainer:c.startContainer,startOffset:c.startOffset,endContainer:c.endContainer,endOffset:c.endOffset})});c.removeChild(a);c.insertBefore(a,e);d.forEach(function(a){var b=a.cursor.getSelectedRange();b.setStart(a.startContainer,a.startOffset);b.setEnd(a.endContainer,a.endOffset)})}var h,
c,g,b;this.init=function(f){h=f.memberid;c=f.timestamp;g=f.position;b=f.text};this.execute=function(p){var a,n,e,d,t=p.getDOM(),l,r=!0,k=0,m;if(a=p.getPositionInTextNode(g,h)){n=a.textNode;e=n.parentNode;d=n.nextSibling;l=p.getParagraphElement(n);a.offset!==n.length&&(d=n.splitText(a.offset));for(a=0;a<b.length;a+=1)if(" "===b[a]||"\t"===b[a])k<a&&(k=b.substring(k,a),r?n.appendData(k):e.insertBefore(t.createTextNode(k),d)),k=a+1,r=!1,m=" "===b[a]?"text:s":"text:tab",m=t.createElementNS("urn:oasis:names:tc:opendocument:xmlns:text:1.0",
m),m.appendChild(t.createTextNode(b[a])),e.insertBefore(m,d);k=b.substring(k);0<k.length&&(r?n.appendData(k):e.insertBefore(t.createTextNode(k),d));f(p,n);0===n.length&&n.parentNode.removeChild(n);p.getOdfCanvas().refreshSize();p.emit(ops.OdtDocument.signalParagraphChanged,{paragraphElement:l,memberId:h,timeStamp:c});p.getOdfCanvas().rerenderAnnotations();return!0}return!1};this.spec=function(){return{optype:"InsertText",memberid:h,timestamp:c,position:g,text:b}}};
// Input 47
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("odf.Namespaces");runtime.loadClass("odf.OdfUtils");runtime.loadClass("core.DomUtils");
ops.OpRemoveText=function(){function f(b){function c(b){if(a.isCharacterElement(b))return!1;if(b.nodeType===Node.TEXT_NODE)return 0===b.textContent.length;for(b=b.firstChild;b;){if(!c(b))return!1;b=b.nextSibling}return!0}function f(g){g=n.mergeIntoParent(g);return!a.isParagraph(g)&&g!==b&&c(g)?f(g):g}this.isEmpty=c;this.mergeChildrenIntoParent=f}function h(a){var c=a.getPositionFilter(),f,g,h,k,m=p,q=a.getDOM().createRange();a=a.getIteratorAtPosition(b);f=a.container();for(g=a.unfilteredDomOffset();m&&
a.nextPosition();)h=a.container(),k=a.unfilteredDomOffset(),c.acceptPosition(a)===NodeFilter.FILTER_ACCEPT&&(m-=1);q.setStart(f,g);q.setEnd(h,k);n.splitBoundaries(q);return q}var c,g,b,p,a,n;this.init=function(e){runtime.assert(0<=e.length,"OpRemoveText only supports positive lengths");c=e.memberid;g=e.timestamp;b=parseInt(e.position,10);p=parseInt(e.length,10);a=new odf.OdfUtils;n=new core.DomUtils};this.execute=function(a){var d,n,l,r,k=new f(a.getRootNode());a.upgradeWhitespacesAtPosition(b);a.upgradeWhitespacesAtPosition(b+
p);n=h(a);d=a.getParagraphElement(n.startContainer);l=a.getTextElements(n,!0);r=a.getParagraphElements(n);n.detach();l.forEach(function(a){k.mergeChildrenIntoParent(a)});n=r.reduce(function(a,b){var c,d,e=a,f=b,g,h;k.isEmpty(a)&&(d=!0,b.parentNode!==a.parentNode&&(g=b.parentNode,a.parentNode.insertBefore(b,a.nextSibling)),f=a,e=b,h=e.getElementsByTagNameNS("urn:webodf:names:editinfo","editinfo")[0]||e.firstChild);for(;f.hasChildNodes();)c=d?f.lastChild:f.firstChild,f.removeChild(c),"editinfo"!==c.localName&&
e.insertBefore(c,h);g&&k.isEmpty(g)&&k.mergeChildrenIntoParent(g);k.mergeChildrenIntoParent(f);return e});a.fixCursorPositions();a.getOdfCanvas().refreshSize();a.emit(ops.OdtDocument.signalParagraphChanged,{paragraphElement:n||d,memberId:c,timeStamp:g});a.emit(ops.OdtDocument.signalCursorMoved,a.getCursor(c));a.getOdfCanvas().rerenderAnnotations();return!0};this.spec=function(){return{optype:"RemoveText",memberid:c,timestamp:g,position:b,length:p}}};
// Input 48
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpSplitParagraph=function(){var f,h,c,g;this.init=function(b){f=b.memberid;h=b.timestamp;c=b.position;g=new odf.OdfUtils};this.execute=function(b){var p,a,n,e,d,t;b.upgradeWhitespacesAtPosition(c);p=b.getPositionInTextNode(c,f);if(!p)return!1;a=b.getParagraphElement(p.textNode);if(!a)return!1;n=g.isListItem(a.parentNode)?a.parentNode:a;0===p.offset?(t=p.textNode.previousSibling,d=null):(t=p.textNode,d=p.offset>=p.textNode.length?null:p.textNode.splitText(p.offset));for(p=p.textNode;p!==n;)if(p=
p.parentNode,e=p.cloneNode(!1),t){for(d&&e.appendChild(d);t.nextSibling;)e.appendChild(t.nextSibling);p.parentNode.insertBefore(e,p.nextSibling);t=p;d=e}else p.parentNode.insertBefore(e,p),t=e,d=p;g.isListItem(d)&&(d=d.childNodes[0]);b.fixCursorPositions(f);b.getOdfCanvas().refreshSize();b.emit(ops.OdtDocument.signalParagraphChanged,{paragraphElement:a,memberId:f,timeStamp:h});b.emit(ops.OdtDocument.signalParagraphChanged,{paragraphElement:d,memberId:f,timeStamp:h});b.getOdfCanvas().rerenderAnnotations();
return!0};this.spec=function(){return{optype:"SplitParagraph",memberid:f,timestamp:h,position:c}}};
// Input 49
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpSetParagraphStyle=function(){var f,h,c,g;this.init=function(b){f=b.memberid;h=b.timestamp;c=b.position;g=b.styleName};this.execute=function(b){var p;if(p=b.getPositionInTextNode(c))if(p=b.getParagraphElement(p.textNode))return""!==g?p.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:text:1.0","text:style-name",g):p.removeAttributeNS("urn:oasis:names:tc:opendocument:xmlns:text:1.0","style-name"),b.getOdfCanvas().refreshSize(),b.emit(ops.OdtDocument.signalParagraphChanged,{paragraphElement:p,
timeStamp:h,memberId:f}),b.getOdfCanvas().rerenderAnnotations(),!0;return!1};this.spec=function(){return{optype:"SetParagraphStyle",memberid:f,timestamp:h,position:c,styleName:g}}};
// Input 50
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpUpdateParagraphStyle=function(){function f(a,b){var c,d,f=b?b.split(","):[];for(c=0;c<f.length;c+=1)d=f[c].split(":"),a.removeAttributeNS(odf.Namespaces.resolvePrefix(d[0]),d[1])}var h,c,g,b,p;this.init=function(a){h=a.memberid;c=a.timestamp;g=a.styleName;b=a.setProperties;p=a.removedProperties};this.execute=function(a){var c=a.getFormatting(),e=a.getDOM(),d=e.createElementNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","style:style"),h,l,r,k,m;return(d=a.getParagraphStyleElement(g))?(h=
d.getElementsByTagNameNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","paragraph-properties")[0],l=d.getElementsByTagNameNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","text-properties")[0],b&&Object.keys(b).forEach(function(f){switch(f){case "style:paragraph-properties":void 0===h&&(h=e.createElementNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","style:paragraph-properties"),d.appendChild(h));c.updateStyle(h,b["style:paragraph-properties"]);break;case "style:text-properties":void 0===
l&&(l=e.createElementNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","style:text-properties"),d.appendChild(l));(k=b["style:text-properties"]["style:font-name"])&&!c.getFontMap().hasOwnProperty(k)&&(r=e.createElementNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","style:font-face"),r.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:style:1.0","style:name",k),r.setAttributeNS("urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0","svg:font-family",k),a.getOdfCanvas().odfContainer().rootElement.fontFaceDecls.appendChild(r));
c.updateStyle(l,b["style:text-properties"]);break;default:"object"!==typeof b[f]&&(m=odf.Namespaces.resolvePrefix(f.substr(0,f.indexOf(":"))),d.setAttributeNS(m,f,b[f]))}}),p&&(p["style:paragraph-properties"]&&(f(h,p["style:paragraph-properties"].attributes),0===h.attributes.length&&d.removeChild(h)),p["style:text-properties"]&&(f(l,p["style:text-properties"].attributes),0===l.attributes.length&&d.removeChild(l)),f(d,p.attributes)),a.getOdfCanvas().refreshCSS(),a.emit(ops.OdtDocument.signalParagraphStyleModified,
g),a.getOdfCanvas().rerenderAnnotations(),!0):!1};this.spec=function(){return{optype:"UpdateParagraphStyle",memberid:h,timestamp:c,styleName:g,setProperties:b,removedProperties:p}}};
// Input 51
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("odf.Namespaces");
ops.OpAddParagraphStyle=function(){var f,h,c,g,b=odf.Namespaces.svgns,p=odf.Namespaces.stylens;this.init=function(a){f=a.memberid;h=a.timestamp;c=a.styleName;g=a.setProperties};this.execute=function(a){var f=a.getOdfCanvas().odfContainer(),e=a.getFormatting(),d=a.getDOM(),h=d.createElementNS(p,"style:style"),l,r,k,m,q;if(!h)return!1;h.setAttributeNS(p,"style:family","paragraph");h.setAttributeNS(p,"style:name",c);g&&Object.keys(g).forEach(function(a){switch(a){case "style:paragraph-properties":l=d.createElementNS(p,
"style:paragraph-properties");h.appendChild(l);e.updateStyle(l,g["style:paragraph-properties"]);break;case "style:text-properties":r=d.createElementNS(p,"style:text-properties");h.appendChild(r);(m=g["style:text-properties"]["style:font-name"])&&!e.getFontMap().hasOwnProperty(m)&&(k=d.createElementNS(p,"style:font-face"),k.setAttributeNS(p,"style:name",m),k.setAttributeNS(b,"svg:font-family",m),f.rootElement.fontFaceDecls.appendChild(k));e.updateStyle(r,g["style:text-properties"]);break;default:"object"!==
typeof g[a]&&(q=odf.Namespaces.resolvePrefix(a.substr(0,a.indexOf(":"))),h.setAttributeNS(q,a,g[a]))}});f.rootElement.styles.appendChild(h);a.getOdfCanvas().refreshCSS();a.emit(ops.OdtDocument.signalStyleCreated,c);return!0};this.spec=function(){return{optype:"AddParagraphStyle",memberid:f,timestamp:h,styleName:c,setProperties:g}}};
// Input 52
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpRemoveParagraphStyle=function(){var f,h,c;this.init=function(g){f=g.memberid;h=g.timestamp;c=g.styleName};this.execute=function(f){var b=f.getParagraphStyleElement(c);if(!b)return!1;b.parentNode.removeChild(b);f.getOdfCanvas().refreshCSS();f.emit(ops.OdtDocument.signalStyleDeleted,c);return!0};this.spec=function(){return{optype:"RemoveParagraphStyle",memberid:f,timestamp:h,styleName:c}}};
// Input 53
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OpAddAnnotation=function(){function f(a,b,c){if(c=a.getPositionInTextNode(c,h))a=c.textNode,c.offset!==a.length&&a.splitText(c.offset),a.parentNode.insertBefore(b,a.nextSibling)}var h,c,g,b,p;this.init=function(a){h=a.memberid;c=parseInt(a.timestamp,10);g=parseInt(a.position,10);b=parseInt(a.length,10)||0;p=a.name};this.execute=function(a){var n={},e=a.getPositionFilter(),d=a.getCursor(h),t=a.getCursorPosition(h),t=g-t-1,l=new Date(c),r,k,m,q,w;w=a.getDOM();r=w.createElementNS(odf.Namespaces.officens,
"office:annotation");r.setAttributeNS(odf.Namespaces.officens,"office:name",p);k=w.createElementNS(odf.Namespaces.dcns,"dc:creator");k.setAttributeNS(odf.Namespaces.webodfns+":names:editinfo","editinfo:memberid",h);m=w.createElementNS(odf.Namespaces.dcns,"dc:date");m.appendChild(w.createTextNode(l.toISOString()));l=w.createElementNS(odf.Namespaces.textns,"text:list");q=w.createElementNS(odf.Namespaces.textns,"text:list-item");w=w.createElementNS(odf.Namespaces.textns,"text:p");q.appendChild(w);l.appendChild(q);
r.appendChild(k);r.appendChild(m);r.appendChild(l);n.node=r;if(!n.node)return!1;if(b){r=a.getDOM().createElementNS(odf.Namespaces.officens,"office:annotation-end");r.setAttributeNS(odf.Namespaces.officens,"office:name",p);n.end=r;if(!n.end)return!1;f(a,n.end,g+b)}f(a,n.node,g);d&&(r=d.getStepCounter(),e=0<t?r.countForwardSteps(t,e):0>t?-r.countBackwardSteps(-t,e):0,d.move(e),a.emit(ops.OdtDocument.signalCursorMoved,d));a.getOdfCanvas().addAnnotation(n);return!0};this.spec=function(){return{optype:"AddAnnotation",
memberid:h,timestamp:c,position:g,length:b,name:p}}};
// Input 54
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("odf.Namespaces");runtime.loadClass("core.DomUtils");
ops.OpRemoveAnnotation=function(){var f,h,c,g,b;this.init=function(p){f=p.memberid;h=p.timestamp;c=parseInt(p.position,10);g=parseInt(p.length,10);b=new core.DomUtils};this.execute=function(f){for(var a=f.getIteratorAtPosition(c).container(),g,e=null,d=null;a.namespaceURI!==odf.Namespaces.officens||"annotation"!==a.localName;)a=a.parentNode;if(null===a)return!1;e=a;(g=e.getAttributeNS(odf.Namespaces.officens,"name"))&&(d=b.getElementsByTagNameNS(f.getRootNode(),odf.Namespaces.officens,"annotation-end").filter(function(a){return g===
a.getAttributeNS(odf.Namespaces.officens,"name")})[0]||null);f.getOdfCanvas().forgetAnnotations();for(a=b.getElementsByTagNameNS(e,odf.Namespaces.webodfns+":names:cursor","cursor");a.length;)e.parentNode.insertBefore(a.pop(),e);e.parentNode.removeChild(e);d&&d.parentNode.removeChild(d);f.fixCursorPositions();f.getOdfCanvas().refreshAnnotations();return!0};this.spec=function(){return{optype:"RemoveAnnotation",memberid:f,timestamp:h,position:c,length:g}}};
// Input 55
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("ops.OpAddCursor");runtime.loadClass("ops.OpApplyDirectStyling");runtime.loadClass("ops.OpRemoveCursor");runtime.loadClass("ops.OpMoveCursor");runtime.loadClass("ops.OpInsertTable");runtime.loadClass("ops.OpInsertText");runtime.loadClass("ops.OpRemoveText");runtime.loadClass("ops.OpSplitParagraph");runtime.loadClass("ops.OpSetParagraphStyle");runtime.loadClass("ops.OpUpdateParagraphStyle");runtime.loadClass("ops.OpAddParagraphStyle");runtime.loadClass("ops.OpRemoveParagraphStyle");
runtime.loadClass("ops.OpAddAnnotation");runtime.loadClass("ops.OpRemoveAnnotation");
ops.OperationFactory=function(){function f(c){return function(){return new c}}var h;this.register=function(c,f){h[c]=f};this.create=function(c){var f=null,b=h[c.optype];b&&(f=b(c),f.init(c));return f};h={AddCursor:f(ops.OpAddCursor),ApplyDirectStyling:f(ops.OpApplyDirectStyling),InsertTable:f(ops.OpInsertTable),InsertText:f(ops.OpInsertText),RemoveText:f(ops.OpRemoveText),SplitParagraph:f(ops.OpSplitParagraph),SetParagraphStyle:f(ops.OpSetParagraphStyle),UpdateParagraphStyle:f(ops.OpUpdateParagraphStyle),
AddParagraphStyle:f(ops.OpAddParagraphStyle),RemoveParagraphStyle:f(ops.OpRemoveParagraphStyle),MoveCursor:f(ops.OpMoveCursor),RemoveCursor:f(ops.OpRemoveCursor),AddAnnotation:f(ops.OpAddAnnotation),RemoveAnnotation:f(ops.OpRemoveAnnotation)}};
// Input 56
runtime.loadClass("core.Cursor");runtime.loadClass("core.PositionIterator");runtime.loadClass("core.PositionFilter");runtime.loadClass("core.LoopWatchDog");runtime.loadClass("odf.OdfUtils");
gui.SelectionMover=function(f,h){function c(){u.setUnfilteredPosition(f.getNode(),0);return u}function g(a,b){var c,d=null;a&&(c=b?a[a.length-1]:a[0]);c&&(d={top:c.top,left:b?c.right:c.left,bottom:c.bottom});return d}function b(a,c,d,e){var f=a.nodeType;d.setStart(a,c);d.collapse(!e);e=g(d.getClientRects(),!0===e);!e&&0<c&&(d.setStart(a,c-1),d.setEnd(a,c),e=g(d.getClientRects(),!0));e||(f===Node.ELEMENT_NODE&&a.childNodes[c-1]?e=b(a,c-1,d,!0):a.nodeType===Node.TEXT_NODE&&0<c?e=b(a,c-1,d,!0):a.previousSibling?
e=b(a.previousSibling,a.previousSibling.nodeType===Node.TEXT_NODE?a.previousSibling.textContent.length:a.previousSibling.childNodes.length,d,!0):a.parentNode&&a.parentNode!==h?e=b(a.parentNode,0,d,!1):(d.selectNode(h),e=g(d.getClientRects(),!1)));runtime.assert(Boolean(e),"No visible rectangle found");return e}function p(a,d,e){var g=a,k=c(),m,l=h.ownerDocument.createRange(),q=f.getSelectedRange()?f.getSelectedRange().cloneRange():h.ownerDocument.createRange(),p,n=runtime.getWindow();for(m=b(k.container(),
k.unfilteredDomOffset(),l);0<g&&e();)g-=1;d?(d=k.container(),k=k.unfilteredDomOffset(),-1===q.comparePoint(d,k)?(q.setStart(d,k),p=!1):q.setEnd(d,k)):(q.setStart(k.container(),k.unfilteredDomOffset()),q.collapse(!0));f.setSelectedRange(q,p);k=c();q=b(k.container(),k.unfilteredDomOffset(),l);if(q.top===m.top||void 0===C)C=q.left;n.clearTimeout(x);x=n.setTimeout(function(){C=void 0},2E3);l.detach();return a-g}function a(a){var b=c();return a.acceptPosition(b)===s?!0:!1}function n(a,b){for(var d=c(),
e=new core.LoopWatchDog(1E3),f=0,g=0;0<a&&d.nextPosition();)f+=1,e.check(),b.acceptPosition(d)===s&&(g+=f,f=0,a-=1);return g}function e(a,b,d){for(var e=c(),f=new core.LoopWatchDog(1E3),g=0,k=0;0<a&&e.nextPosition();)f.check(),d.acceptPosition(e)===s&&(g+=1,b.acceptPosition(e)===s&&(k+=g,g=0,a-=1));return k}function d(a,b,d){for(var e=c(),f=new core.LoopWatchDog(1E3),g=0,k=0;0<a&&e.previousPosition();)f.check(),d.acceptPosition(e)===s&&(g+=1,b.acceptPosition(e)===s&&(k+=g,g=0,a-=1));return k}function t(a,
b){for(var d=c(),e=new core.LoopWatchDog(1E3),f=0,g=0;0<a&&d.previousPosition();)f+=1,e.check(),b.acceptPosition(d)===s&&(g+=f,f=0,a-=1);return g}function l(a){var b=c(),d=w.getParagraphElement(b.getCurrentNode()),e;e=-t(1,a);if(0===e||d&&d!==w.getParagraphElement(b.getCurrentNode()))e=n(1,a);return e}function r(a,d){var e=c(),f=0,g=0,k=0>a?-1:1;for(a=Math.abs(a);0<a;){for(var m=d,l=k,q=e,p=q.container(),n=0,r=null,u=void 0,w=10,t=void 0,x=0,X=void 0,U=void 0,M=void 0,t=void 0,G=h.ownerDocument.createRange(),
H=new core.LoopWatchDog(1E3),t=b(p,q.unfilteredDomOffset(),G),X=t.top,U=void 0===C?t.left:C,M=X;!0===(0>l?q.previousPosition():q.nextPosition());)if(H.check(),m.acceptPosition(q)===s&&(n+=1,p=q.container(),t=b(p,q.unfilteredDomOffset(),G),t.top!==X)){if(t.top!==M&&M!==X)break;M=t.top;t=Math.abs(U-t.left);if(null===r||t<w)r=p,u=q.unfilteredDomOffset(),w=t,x=n}null!==r?(q.setUnfilteredPosition(r,u),n=x):n=0;G.detach();f+=n;if(0===f)break;g+=f;a-=1}return g*k}function k(a,d){var e,f,g,k,m=c(),q=w.getParagraphElement(m.getCurrentNode()),
l=0,p=h.ownerDocument.createRange();0>a?(e=m.previousPosition,f=-1):(e=m.nextPosition,f=1);for(g=b(m.container(),m.unfilteredDomOffset(),p);e.call(m);)if(d.acceptPosition(m)===s){if(w.getParagraphElement(m.getCurrentNode())!==q)break;k=b(m.container(),m.unfilteredDomOffset(),p);if(k.bottom!==g.bottom&&(g=k.top>=g.top&&k.bottom<g.bottom||k.top<=g.top&&k.bottom>g.bottom,!g))break;l+=f;g=k}p.detach();return l}function m(a,b){for(var c=0,d;a.parentNode!==b;)runtime.assert(null!==a.parentNode,"parent is null"),
a=a.parentNode;for(d=b.firstChild;d!==a;)c+=1,d=d.nextSibling;return c}function q(a,b,d){runtime.assert(null!==a,"SelectionMover.countStepsToPosition called with element===null");var e=c(),f=e.container(),g=e.unfilteredDomOffset(),k=0,h=new core.LoopWatchDog(1E3);e.setUnfilteredPosition(a,b);a=e.container();runtime.assert(Boolean(a),"SelectionMover.countStepsToPosition: positionIterator.container() returned null");b=e.unfilteredDomOffset();e.setUnfilteredPosition(f,g);var f=a,g=b,q=e.container(),
l=e.unfilteredDomOffset();if(f===q)f=l-g;else{var p=f.compareDocumentPosition(q);2===p?p=-1:4===p?p=1:10===p?(g=m(f,q),p=g<l?1:-1):(l=m(q,f),p=l<g?-1:1);f=p}if(0>f)for(;e.nextPosition()&&(h.check(),d.acceptPosition(e)===s&&(k+=1),e.container()!==a||e.unfilteredDomOffset()!==b););else if(0<f)for(;e.previousPosition()&&(h.check(),d.acceptPosition(e)===s&&(k-=1),e.container()!==a||e.unfilteredDomOffset()!==b););return k}var w,u,C,x,s=core.PositionFilter.FilterResult.FILTER_ACCEPT;this.movePointForward=
function(a,b){return p(a,b,u.nextPosition)};this.movePointBackward=function(a,b){return p(a,b,u.previousPosition)};this.getStepCounter=function(){return{countForwardSteps:n,countBackwardSteps:t,convertForwardStepsBetweenFilters:e,convertBackwardStepsBetweenFilters:d,countLinesSteps:r,countStepsToLineBoundary:k,countStepsToPosition:q,isPositionWalkable:a,countStepsToValidPosition:l}};(function(){w=new odf.OdfUtils;u=gui.SelectionMover.createPositionIterator(h);var a=h.ownerDocument.createRange();a.setStart(u.container(),
u.unfilteredDomOffset());a.collapse(!0);f.setSelectedRange(a)})()};gui.SelectionMover.createPositionIterator=function(f){var h=new function(){this.acceptNode=function(c){return"urn:webodf:names:cursor"===c.namespaceURI||"urn:webodf:names:editinfo"===c.namespaceURI?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}};return new core.PositionIterator(f,5,h,!1)};(function(){return gui.SelectionMover})();
// Input 57
runtime.loadClass("core.Cursor");runtime.loadClass("gui.SelectionMover");
ops.OdtCursor=function(f,h){var c=this,g,b;this.removeFromOdtDocument=function(){b.remove()};this.move=function(b,a){var f=0;0<b?f=g.movePointForward(b,a):0>=b&&(f=-g.movePointBackward(-b,a));c.handleUpdate();return f};this.handleUpdate=function(){};this.getStepCounter=function(){return g.getStepCounter()};this.getMemberId=function(){return f};this.getNode=function(){return b.getNode()};this.getAnchorNode=function(){return b.getAnchorNode()};this.getSelectedRange=function(){return b.getSelectedRange()};
this.getOdtDocument=function(){return h};b=new core.Cursor(h.getDOM(),f);g=new gui.SelectionMover(b,h.getRootNode())};
// Input 58
/*

 Copyright (C) 2012 KO GmbH <aditya.bhatt@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.EditInfo=function(f,h){function c(){var c=[],a;for(a in b)b.hasOwnProperty(a)&&c.push({memberid:a,time:b[a].time});c.sort(function(a,b){return a.time-b.time});return c}var g,b={};this.getNode=function(){return g};this.getOdtDocument=function(){return h};this.getEdits=function(){return b};this.getSortedEdits=function(){return c()};this.addEdit=function(c,a){b[c]={time:a}};this.clearEdits=function(){b={}};g=h.getDOM().createElementNS("urn:webodf:names:editinfo","editinfo");f.insertBefore(g,f.firstChild)};
// Input 59
gui.Avatar=function(f,h){var c=this,g,b,p;this.setColor=function(a){b.style.borderColor=a};this.setImageUrl=function(a){c.isVisible()?b.src=a:p=a};this.isVisible=function(){return"block"===g.style.display};this.show=function(){p&&(b.src=p,p=void 0);g.style.display="block"};this.hide=function(){g.style.display="none"};this.markAsFocussed=function(a){g.className=a?"active":""};(function(){var a=f.ownerDocument,c=a.documentElement.namespaceURI;g=a.createElementNS(c,"div");b=a.createElementNS(c,"img");
b.width=64;b.height=64;g.appendChild(b);g.style.width="64px";g.style.height="70px";g.style.position="absolute";g.style.top="-80px";g.style.left="-34px";g.style.display=h?"block":"none";f.appendChild(g)})()};
// Input 60
runtime.loadClass("gui.Avatar");runtime.loadClass("ops.OdtCursor");
gui.Caret=function(f,h,c){function g(c){n&&a.parentNode&&(!e||c)&&(c&&void 0!==d&&runtime.clearTimeout(d),e=!0,b.style.opacity=c||"0"===b.style.opacity?"1":"0",d=runtime.setTimeout(function(){e=!1;g(!1)},500))}var b,p,a,n=!1,e=!1,d;this.refreshCursorBlinking=function(){c||f.getSelectedRange().collapsed?(n=!0,g(!0)):(n=!1,b.style.opacity="0")};this.setFocus=function(){n=!0;p.markAsFocussed(!0);g(!0)};this.removeFocus=function(){n=!1;p.markAsFocussed(!1);b.style.opacity="0"};this.setAvatarImageUrl=
function(a){p.setImageUrl(a)};this.setColor=function(a){b.style.borderColor=a;p.setColor(a)};this.getCursor=function(){return f};this.getFocusElement=function(){return b};this.toggleHandleVisibility=function(){p.isVisible()?p.hide():p.show()};this.showHandle=function(){p.show()};this.hideHandle=function(){p.hide()};this.ensureVisible=function(){var a,c,d,e,g=f.getOdtDocument().getOdfCanvas().getElement().parentNode,h;d=g.offsetWidth-g.clientWidth+5;e=g.offsetHeight-g.clientHeight+5;h=b.getBoundingClientRect();
a=h.left-d;c=h.top-e;d=h.right+d;e=h.bottom+e;h=g.getBoundingClientRect();c<h.top?g.scrollTop-=h.top-c:e>h.bottom&&(g.scrollTop+=e-h.bottom);a<h.left?g.scrollLeft-=h.left-a:d>h.right&&(g.scrollLeft+=d-h.right)};(function(){var c=f.getOdtDocument().getDOM();b=c.createElementNS(c.documentElement.namespaceURI,"span");a=f.getNode();a.appendChild(b);p=new gui.Avatar(a,h)})()};
// Input 61
runtime.loadClass("core.EventNotifier");
gui.ClickHandler=function(){function f(){c=0;g=null}var h,c=0,g=null,b=new core.EventNotifier([gui.ClickHandler.signalSingleClick,gui.ClickHandler.signalDoubleClick,gui.ClickHandler.signalTripleClick]);this.subscribe=function(c,a){b.subscribe(c,a)};this.handleMouseUp=function(p){var a=runtime.getWindow();g&&g.x===p.screenX&&g.y===p.screenY?(c+=1,1===c?b.emit(gui.ClickHandler.signalSingleClick,p):2===c?b.emit(gui.ClickHandler.signalDoubleClick,void 0):3===c&&(a.clearTimeout(h),b.emit(gui.ClickHandler.signalTripleClick,
void 0),f())):(b.emit(gui.ClickHandler.signalSingleClick,p),c=1,g={x:p.screenX,y:p.screenY},a.clearTimeout(h),h=a.setTimeout(f,400))}};gui.ClickHandler.signalSingleClick="click";gui.ClickHandler.signalDoubleClick="doubleClick";gui.ClickHandler.signalTripleClick="tripleClick";(function(){return gui.ClickHandler})();
// Input 62
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
gui.KeyboardHandler=function(){function f(b,c){c||(c=h.None);return b+":"+c}var h=gui.KeyboardHandler.Modifier,c=null,g={};this.setDefault=function(b){c=b};this.bind=function(b,c,a){b=f(b,c);runtime.assert(!1===g.hasOwnProperty(b),"tried to overwrite the callback handler of key combo: "+b);g[b]=a};this.unbind=function(b,c){var a=f(b,c);delete g[a]};this.reset=function(){c=null;g={}};this.handleEvent=function(b){var p=b.keyCode,a=h.None;b.metaKey&&(a|=h.Meta);b.ctrlKey&&(a|=h.Ctrl);b.altKey&&(a|=h.Alt);
b.shiftKey&&(a|=h.Shift);p=f(p,a);p=g[p];a=!1;p?a=p():null!==c&&(a=c(b));a&&(b.preventDefault?b.preventDefault():b.returnValue=!1)}};gui.KeyboardHandler.Modifier={None:0,Meta:1,Ctrl:2,Alt:4,Shift:8,MetaShift:9,CtrlShift:10,AltShift:12};gui.KeyboardHandler.KeyCode={Backspace:8,Tab:9,Clear:12,Enter:13,End:35,Home:36,Left:37,Up:38,Right:39,Down:40,Delete:46,A:65,B:66,I:73,U:85,Z:90};(function(){return gui.KeyboardHandler})();
// Input 63
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("odf.Namespaces");runtime.loadClass("xmldom.LSSerializer");runtime.loadClass("odf.OdfNodeFilter");runtime.loadClass("odf.TextSerializer");
gui.Clipboard=function(){var f,h,c;this.setDataFromRange=function(c,b){var p=!0,a,n=c.clipboardData;a=runtime.getWindow();var e=b.startContainer.ownerDocument;!n&&a&&(n=a.clipboardData);n?(e=e.createElement("span"),e.appendChild(b.cloneContents()),a=n.setData("text/plain",h.writeToString(e)),p=p&&a,a=n.setData("text/html",f.writeToString(e,odf.Namespaces.namespaceMap)),p=p&&a,c.preventDefault()):p=!1;return p};f=new xmldom.LSSerializer;h=new odf.TextSerializer;c=new odf.OdfNodeFilter;f.filter=c;h.filter=
c};
// Input 64
runtime.loadClass("core.DomUtils");runtime.loadClass("odf.OdfUtils");runtime.loadClass("ops.OpAddCursor");runtime.loadClass("ops.OpRemoveCursor");runtime.loadClass("ops.OpMoveCursor");runtime.loadClass("ops.OpInsertText");runtime.loadClass("ops.OpRemoveText");runtime.loadClass("ops.OpSplitParagraph");runtime.loadClass("ops.OpSetParagraphStyle");runtime.loadClass("ops.OpRemoveAnnotation");runtime.loadClass("gui.ClickHandler");runtime.loadClass("gui.Clipboard");runtime.loadClass("gui.KeyboardHandler");
runtime.loadClass("gui.StyleHelper");
gui.SessionController=function(){gui.SessionController=function(f,h){function c(a,b,c,d){var e="on"+b,f=!1;a.attachEvent&&(f=a.attachEvent(e,c));!f&&a.addEventListener&&(a.addEventListener(b,c,!1),f=!0);f&&!d||!a.hasOwnProperty(e)||(a[e]=c)}function g(a,b,c){var d="on"+b;a.detachEvent&&a.detachEvent(d,c);a.removeEventListener&&a.removeEventListener(b,c,!1);a[d]===c&&(a[d]=null)}function b(a){a.preventDefault?a.preventDefault():a.returnValue=!1}function p(a,b){var c=new ops.OpMoveCursor;c.init({memberid:h,
position:a,length:b||0});return c}function a(a,b){var c=gui.SelectionMover.createPositionIterator(z.getRootNode()),d=z.getOdfCanvas().getElement(),e;e=a;if(!e)return null;for(;e!==d&&!("urn:webodf:names:cursor"===e.namespaceURI&&"cursor"===e.localName||"urn:webodf:names:editinfo"===e.namespaceURI&&"editinfo"===e.localName);)if(e=e.parentNode,!e)return null;e!==d&&a!==e&&(a=e.parentNode,b=Array.prototype.indexOf.call(a.childNodes,e));c.setUnfilteredPosition(a,b);return z.getDistanceFromCursor(h,c.container(),
c.unfilteredDomOffset())}function n(a){var b=z.getOdfCanvas().getElement(),c=z.getRootNode(),d=0;b.compareDocumentPosition(a)&Node.DOCUMENT_POSITION_PRECEDING||(a=gui.SelectionMover.createPositionIterator(c),a.moveToEnd(),c=a.container(),d=a.unfilteredDomOffset());return{node:c,offset:d}}function e(b){runtime.setTimeout(function(){var c;a:{var d=z.getOdfCanvas().getElement(),e=da.getSelection(),g,k,m,l;if(null===e.anchorNode&&null===e.focusNode){c=b.clientX;g=b.clientY;k=z.getDOM();k.caretRangeFromPoint?
(c=k.caretRangeFromPoint(c,g),g={container:c.startContainer,offset:c.startOffset}):k.caretPositionFromPoint?(c=k.caretPositionFromPoint(c,g),g={container:c.offsetNode,offset:c.offset}):g=null;if(!g){c=null;break a}c=g.container;g=g.offset;k=c;e=g}else c=e.anchorNode,g=e.anchorOffset,k=e.focusNode,e=e.focusOffset;runtime.assert(null!==c&&null!==k,"anchorNode is null or focusNode is null");m=ra.containsNode(d,c);l=ra.containsNode(d,k);m||l?(m||(m=n(c),c=m.node,g=m.offset),l||(m=n(k),k=m.node,e=m.offset),
d.focus(),c={anchorNode:c,anchorOffset:g,focusNode:k,focusOffset:e}):c=null}null!==c&&(d=a(c.anchorNode,c.anchorOffset),g=c.focusNode===c.anchorNode&&c.focusOffset===c.anchorOffset?d:a(c.focusNode,c.focusOffset),null!==g&&0!==g||null!==d&&0!==d)&&(c=z.getCursorPosition(h),d=p(c+d,g-d),f.enqueue(d))},0)}function d(a){e(a)}function t(){var a=z.getOdfCanvas().getElement(),b=/[A-Za-z0-9]/,c=0,d=0,e,g;if(ra.containsNode(a,da.getSelection().focusNode)){a=gui.SelectionMover.createPositionIterator(z.getRootNode());
e=z.getCursor(h).getNode();for(a.setUnfilteredPosition(e,0);a.previousPosition();)if(g=a.getCurrentNode(),g.nodeType===Node.TEXT_NODE){g=g.data[a.unfilteredDomOffset()];if(!b.test(g))break;c-=1}else if(g.namespaceURI!==odf.Namespaces.textns||"span"!==g.localName)break;a.setUnfilteredPosition(e,0);do if(g=a.getCurrentNode(),g.nodeType===Node.TEXT_NODE){g=g.data[a.unfilteredDomOffset()];if(!b.test(g))break;d+=1}else if(g.namespaceURI!==odf.Namespaces.textns||"span"!==g.localName)break;while(a.nextPosition());
if(0!==c||0!==d)b=z.getCursorPosition(h),c=p(b+c,Math.abs(c)+Math.abs(d)),f.enqueue(c)}}function l(){var a=z.getOdfCanvas().getElement(),b,c;ra.containsNode(a,da.getSelection().focusNode)&&(c=z.getParagraphElement(z.getCursor(h).getNode()),a=z.getDistanceFromCursor(h,c,0),b=gui.SelectionMover.createPositionIterator(z.getRootNode()),b.moveToEndOfNode(c),c=z.getDistanceFromCursor(h,c,b.unfilteredDomOffset()),0!==a||0!==c)&&(b=z.getCursorPosition(h),a=p(b+a,Math.abs(a)+Math.abs(c)),f.enqueue(a))}function r(a){var b=
z.getCursorSelection(h),c=z.getCursor(h).getStepCounter();0!==a&&(a=0<a?c.convertForwardStepsBetweenFilters(a,ka,ma):-c.convertBackwardStepsBetweenFilters(-a,ka,ma),a=b.length+a,f.enqueue(p(b.position,a)))}function k(a){var b=z.getCursorPosition(h),c=z.getCursor(h).getStepCounter();0!==a&&(a=0<a?c.convertForwardStepsBetweenFilters(a,ka,ma):-c.convertBackwardStepsBetweenFilters(-a,ka,ma),f.enqueue(p(b+a,0)))}function m(){k(-1);return!0}function q(){k(1);return!0}function w(){r(-1);return!0}function u(){r(1);
return!0}function C(a,b){var c=z.getParagraphElement(z.getCursor(h).getNode());runtime.assert(Boolean(c),"SessionController: Cursor outside paragraph");c=z.getCursor(h).getStepCounter().countLinesSteps(a,ka);b?r(c):k(c)}function x(){C(-1,!1);return!0}function s(){C(1,!1);return!0}function v(){C(-1,!0);return!0}function y(){C(1,!0);return!0}function E(a,b){var c=z.getCursor(h).getStepCounter().countStepsToLineBoundary(a,ka);b?r(c):k(c)}function D(){E(-1,!1);return!0}function N(){E(1,!1);return!0}function A(){E(-1,
!0);return!0}function O(){E(1,!0);return!0}function B(){var a=z.getParagraphElement(z.getCursor(h).getNode()),b,c;runtime.assert(Boolean(a),"SessionController: Cursor outside paragraph");c=z.getDistanceFromCursor(h,a,0);b=gui.SelectionMover.createPositionIterator(z.getRootNode());for(b.setUnfilteredPosition(a,0);0===c&&b.previousPosition();)a=b.getCurrentNode(),sa.isParagraph(a)&&(c=z.getDistanceFromCursor(h,a,0));r(c);return!0}function J(){var a=z.getParagraphElement(z.getCursor(h).getNode()),b,
c;runtime.assert(Boolean(a),"SessionController: Cursor outside paragraph");b=gui.SelectionMover.createPositionIterator(z.getRootNode());b.moveToEndOfNode(a);for(c=z.getDistanceFromCursor(h,b.container(),b.unfilteredDomOffset());0===c&&b.nextPosition();)a=b.getCurrentNode(),sa.isParagraph(a)&&(b.moveToEndOfNode(a),c=z.getDistanceFromCursor(h,b.container(),b.unfilteredDomOffset()));r(c);return!0}function L(a,b){var c=gui.SelectionMover.createPositionIterator(z.getRootNode());0<a&&c.moveToEnd();c=z.getDistanceFromCursor(h,
c.container(),c.unfilteredDomOffset());b?r(c):k(c)}function ea(){L(-1,!1);return!0}function fa(){L(1,!1);return!0}function aa(){L(-1,!0);return!0}function ba(){L(1,!0);return!0}function ga(){var a=gui.SelectionMover.createPositionIterator(z.getRootNode()),b;b=-z.getDistanceFromCursor(h,a.container(),a.unfilteredDomOffset());a.moveToEnd();b+=z.getDistanceFromCursor(h,a.container(),a.unfilteredDomOffset());f.enqueue(p(0,b));return!0}function P(a){0>a.length&&(a.position+=a.length,a.length=-a.length);
return a}function X(a){var b=new ops.OpRemoveText;b.init({memberid:h,position:a.position,length:a.length});return b}function U(){var a=P(z.getCursorSelection(h)),b=null;0===a.length?0<a.position&&z.getPositionInTextNode(a.position-1)&&(b=new ops.OpRemoveText,b.init({memberid:h,position:a.position-1,length:1}),f.enqueue(b)):(b=X(a),f.enqueue(b));return!0}function M(){var a=P(z.getCursorSelection(h)),b=null;0===a.length?z.getPositionInTextNode(a.position+1)&&(b=new ops.OpRemoveText,b.init({memberid:h,
position:a.position,length:1}),f.enqueue(b)):(b=X(a),f.enqueue(b));return null!==b}function G(){var a=P(z.getCursorSelection(h));0!==a.length&&f.enqueue(X(a));return!0}function H(a){var b=P(z.getCursorSelection(h)),c=null;0<b.length&&(c=X(b),f.enqueue(c));c=new ops.OpInsertText;c.init({memberid:h,position:b.position,text:a});f.enqueue(c)}function R(){var a=z.getCursorPosition(h),b;b=new ops.OpSplitParagraph;b.init({memberid:h,position:a});f.enqueue(b);return!0}function Q(){var a=z.getCursor(h),b=
da.getSelection();a&&(b.removeAllRanges(),b.addRange(a.getSelectedRange().cloneRange()))}function Z(a){var b=z.getCursor(h);b.getSelectedRange().collapsed||(wa.setDataFromRange(a,b.getSelectedRange())?(b=new ops.OpRemoveText,a=P(f.getOdtDocument().getCursorSelection(h)),b.init({memberid:h,position:a.position,length:a.length}),f.enqueue(b)):runtime.log("Cut operation failed"))}function $(){return!1!==z.getCursor(h).getSelectedRange().collapsed}function ha(a){var b=z.getCursor(h);b.getSelectedRange().collapsed||
wa.setDataFromRange(a,b.getSelectedRange())||runtime.log("Cut operation failed")}function na(a){var b;da.clipboardData&&da.clipboardData.getData?b=da.clipboardData.getData("Text"):a.clipboardData&&a.clipboardData.getData&&(b=a.clipboardData.getData("text/plain"));b&&(H(b),a.preventDefault?a.preventDefault():a.returnValue=!1)}function K(){return!1}function F(a){if(ca)ca.onOperationExecuted(a)}function ja(a){z.emit(ops.OdtDocument.signalUndoStackChanged,a)}function oa(){return ca?(ca.moveBackward(1),
Q(),!0):!1}function W(){return ca?(ca.moveForward(1),Q(),!0):!1}function T(a,b){var c=z.getCursorSelection(h),d=new ops.OpApplyDirectStyling,e={};e[a]=b;d.init({memberid:h,position:c.position,length:c.length,setProperties:{"style:text-properties":e}});f.enqueue(d)}function ia(){var a=z.getCursor(h).getSelectedRange(),a=ta.isBold(a)?"normal":"bold";T("fo:font-weight",a);return!0}function Y(){var a=z.getCursor(h).getSelectedRange(),a=ta.isItalic(a)?"normal":"italic";T("fo:font-style",a);return!0}function la(){var a=
z.getCursor(h).getSelectedRange(),a=ta.hasUnderline(a)?"none":"solid";T("style:text-underline-style",a);return!0}var da=runtime.getWindow(),z=f.getOdtDocument(),ra=new core.DomUtils,sa=new odf.OdfUtils,wa=new gui.Clipboard,pa=new gui.ClickHandler,I=new gui.KeyboardHandler,ua=new gui.KeyboardHandler,ta=new gui.StyleHelper(z.getFormatting()),ka=new core.PositionFilterChain,ma=z.getPositionFilter(),ca=null;runtime.assert(null!==da,"Expected to be run in an environment which has a global window, like a browser.");
ka.addFilter("BaseFilter",ma);ka.addFilter("RootFilter",z.createRootFilter(h));this.startEditing=function(){var a;a=z.getOdfCanvas().getElement();c(a,"keydown",I.handleEvent);c(a,"keypress",ua.handleEvent);c(a,"keyup",b);c(a,"beforecut",$,!0);c(a,"cut",Z);c(a,"copy",ha);c(a,"beforepaste",K,!0);c(a,"paste",na);c(da,"mouseup",pa.handleMouseUp);c(a,"contextmenu",d);z.subscribe(ops.OdtDocument.signalOperationExecuted,Q);z.subscribe(ops.OdtDocument.signalOperationExecuted,F);a=new ops.OpAddCursor;a.init({memberid:h});
f.enqueue(a);ca&&ca.saveInitialState()};this.endEditing=function(){var a;z.unsubscribe(ops.OdtDocument.signalOperationExecuted,F);z.unsubscribe(ops.OdtDocument.signalOperationExecuted,Q);a=z.getOdfCanvas().getElement();g(a,"keydown",I.handleEvent);g(a,"keypress",ua.handleEvent);g(a,"keyup",b);g(a,"cut",Z);g(a,"beforecut",$);g(a,"copy",ha);g(a,"paste",na);g(a,"beforepaste",K);g(da,"mouseup",pa.handleMouseUp);g(a,"contextmenu",d);a=new ops.OpRemoveCursor;a.init({memberid:h});f.enqueue(a);ca&&ca.resetInitialState()};
this.getInputMemberId=function(){return h};this.getSession=function(){return f};this.setUndoManager=function(a){ca&&ca.unsubscribe(gui.UndoManager.signalUndoStackChanged,ja);if(ca=a)ca.setOdtDocument(z),ca.setPlaybackFunction(function(a){a.execute(z)}),ca.subscribe(gui.UndoManager.signalUndoStackChanged,ja)};this.getUndoManager=function(){return ca};(function(){var a=-1!==da.navigator.appVersion.toLowerCase().indexOf("mac"),b=gui.KeyboardHandler.Modifier,c=gui.KeyboardHandler.KeyCode;I.bind(c.Tab,
b.None,function(){H("\t");return!0});I.bind(c.Left,b.None,m);I.bind(c.Right,b.None,q);I.bind(c.Up,b.None,x);I.bind(c.Down,b.None,s);I.bind(c.Backspace,b.None,U);I.bind(c.Delete,b.None,M);I.bind(c.Left,b.Shift,w);I.bind(c.Right,b.Shift,u);I.bind(c.Up,b.Shift,v);I.bind(c.Down,b.Shift,y);I.bind(c.Home,b.None,D);I.bind(c.End,b.None,N);I.bind(c.Home,b.Ctrl,ea);I.bind(c.End,b.Ctrl,fa);I.bind(c.Home,b.Shift,A);I.bind(c.End,b.Shift,O);I.bind(c.Up,b.CtrlShift,B);I.bind(c.Down,b.CtrlShift,J);I.bind(c.Home,
b.CtrlShift,aa);I.bind(c.End,b.CtrlShift,ba);a?(I.bind(c.Clear,b.None,G),I.bind(c.Left,b.Meta,D),I.bind(c.Right,b.Meta,N),I.bind(c.Home,b.Meta,ea),I.bind(c.End,b.Meta,fa),I.bind(c.Left,b.MetaShift,A),I.bind(c.Right,b.MetaShift,O),I.bind(c.Up,b.AltShift,B),I.bind(c.Down,b.AltShift,J),I.bind(c.Up,b.MetaShift,aa),I.bind(c.Down,b.MetaShift,ba),I.bind(c.A,b.Meta,ga),I.bind(c.B,b.Meta,ia),I.bind(c.I,b.Meta,Y),I.bind(c.U,b.Meta,la),I.bind(c.Z,b.Meta,oa),I.bind(c.Z,b.MetaShift,W)):(I.bind(c.A,b.Ctrl,ga),
I.bind(c.B,b.Ctrl,ia),I.bind(c.I,b.Ctrl,Y),I.bind(c.U,b.Ctrl,la),I.bind(c.Z,b.Ctrl,oa),I.bind(c.Z,b.CtrlShift,W));ua.setDefault(function(a){var b;b=null===a.which?String.fromCharCode(a.keyCode):0!==a.which&&0!==a.charCode?String.fromCharCode(a.which):null;return!b||a.altKey||a.ctrlKey||a.metaKey?!1:(H(b),!0)});ua.bind(c.Enter,b.None,R);pa.subscribe(gui.ClickHandler.signalSingleClick,function(a){var b=a.target,c=null;if("annotationRemoveButton"===b.className){a=c=ra.getElementsByTagNameNS(b.parentNode,
odf.Namespaces.officens,"annotation")[0];for(var b=0,c=gui.SelectionMover.createPositionIterator(z.getRootNode()),d=new core.LoopWatchDog(1E3),g=!1;c.nextPosition();)if(d.check(),g=Boolean(a.compareDocumentPosition(c.container())&Node.DOCUMENT_POSITION_CONTAINED_BY),1===ma.acceptPosition(c)){if(g)break;b+=1}c=0;d=gui.SelectionMover.createPositionIterator(z.getRootNode());g=!1;d.setUnfilteredPosition(a,0);do{g=Boolean(a.compareDocumentPosition(d.container())&Node.DOCUMENT_POSITION_CONTAINED_BY);if(!g&&
a!==d.container())break;1===ma.acceptPosition(d)&&(c+=1)}while(d.nextPosition());a=c;c=new ops.OpRemoveAnnotation;c.init({memberid:h,position:b,length:a});f.enqueue(c)}else e(a)});pa.subscribe(gui.ClickHandler.signalDoubleClick,t);pa.subscribe(gui.ClickHandler.signalTripleClick,l)})()};return gui.SessionController}();
// Input 65
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.MemberModel=function(){};ops.MemberModel.prototype.getMemberDetailsAndUpdates=function(f,h){};ops.MemberModel.prototype.unsubscribeMemberDetailsUpdates=function(f,h){};
// Input 66
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.TrivialMemberModel=function(){this.getMemberDetailsAndUpdates=function(f,h){h(f,null)};this.unsubscribeMemberDetailsUpdates=function(f,h){}};
// Input 67
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.OperationRouter=function(){};ops.OperationRouter.prototype.setOperationFactory=function(f){};ops.OperationRouter.prototype.setPlaybackFunction=function(f){};ops.OperationRouter.prototype.push=function(f){};
// Input 68
/*

 Copyright (C) 2012 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
ops.TrivialOperationRouter=function(){var f,h;this.setOperationFactory=function(c){f=c};this.setPlaybackFunction=function(c){h=c};this.push=function(c){c=c.spec();c.timestamp=(new Date).getTime();c=f.create(c);h(c)}};
// Input 69
gui.EditInfoHandle=function(f){var h=[],c,g=f.ownerDocument,b=g.documentElement.namespaceURI;this.setEdits=function(f){h=f;var a,n,e,d;c.innerHTML="";for(f=0;f<h.length;f+=1)a=g.createElementNS(b,"div"),a.className="editInfo",n=g.createElementNS(b,"span"),n.className="editInfoColor",n.setAttributeNS("urn:webodf:names:editinfo","editinfo:memberid",h[f].memberid),e=g.createElementNS(b,"span"),e.className="editInfoAuthor",e.setAttributeNS("urn:webodf:names:editinfo","editinfo:memberid",h[f].memberid),
d=g.createElementNS(b,"span"),d.className="editInfoTime",d.setAttributeNS("urn:webodf:names:editinfo","editinfo:memberid",h[f].memberid),d.innerHTML=h[f].time,a.appendChild(n),a.appendChild(e),a.appendChild(d),c.appendChild(a)};this.show=function(){c.style.display="block"};this.hide=function(){c.style.display="none"};c=g.createElementNS(b,"div");c.setAttribute("class","editInfoHandle");c.style.display="none";f.appendChild(c)};
// Input 70
runtime.loadClass("ops.EditInfo");runtime.loadClass("gui.EditInfoHandle");
gui.EditInfoMarker=function(f,h){function c(b,c){return runtime.getWindow().setTimeout(function(){a.style.opacity=b},c)}var g=this,b,p,a,n,e;this.addEdit=function(b,g){var h=Date.now()-g;f.addEdit(b,g);p.setEdits(f.getSortedEdits());a.setAttributeNS("urn:webodf:names:editinfo","editinfo:memberid",b);if(n){var r=n;runtime.getWindow().clearTimeout(r)}e&&(r=e,runtime.getWindow().clearTimeout(r));1E4>h?(c(1,0),n=c(0.5,1E4-h),e=c(0.2,2E4-h)):1E4<=h&&2E4>h?(c(0.5,0),e=c(0.2,2E4-h)):c(0.2,0)};this.getEdits=
function(){return f.getEdits()};this.clearEdits=function(){f.clearEdits();p.setEdits([]);a.hasAttributeNS("urn:webodf:names:editinfo","editinfo:memberid")&&a.removeAttributeNS("urn:webodf:names:editinfo","editinfo:memberid")};this.getEditInfo=function(){return f};this.show=function(){a.style.display="block"};this.hide=function(){g.hideHandle();a.style.display="none"};this.showHandle=function(){p.show()};this.hideHandle=function(){p.hide()};(function(){var c=f.getOdtDocument().getDOM();a=c.createElementNS(c.documentElement.namespaceURI,
"div");a.setAttribute("class","editInfoMarker");a.onmouseover=function(){g.showHandle()};a.onmouseout=function(){g.hideHandle()};b=f.getNode();b.appendChild(a);p=new gui.EditInfoHandle(b);h||g.hide()})()};
// Input 71
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("gui.Caret");runtime.loadClass("ops.TrivialMemberModel");runtime.loadClass("ops.EditInfo");runtime.loadClass("gui.EditInfoMarker");gui.SessionViewOptions=function(){this.caretBlinksOnRangeSelect=this.caretAvatarsInitiallyVisible=this.editInfoMarkersInitiallyVisible=!0};
gui.SessionView=function(){return function(f,h,c){function g(a,b,c){function e(b,c,f){c=b+'[editinfo|memberid^="'+a+'"]'+f+c;a:{var g=d.firstChild;for(b=b+'[editinfo|memberid^="'+a+'"]'+f;g;){if(g.nodeType===Node.TEXT_NODE&&0===g.data.indexOf(b)){b=g;break a}g=g.nextSibling}b=null}b?b.data=c:d.appendChild(document.createTextNode(c))}e("div.editInfoMarker","{ background-color: "+c+"; }","");e("span.editInfoColor","{ background-color: "+c+"; }","");e("span.editInfoAuthor",'{ content: "'+b+'"; }',":before");
e("dc|creator",'{ content: "'+b+'"; display: none;}',":before");e("dc|creator","{ background-color: "+c+"; }","")}function b(a){var b,c;for(c in t)t.hasOwnProperty(c)&&(b=t[c],a?b.show():b.hide())}function p(a){c.getCarets().forEach(function(b){a?b.showHandle():b.hideHandle()})}function a(a,b){var d=c.getCaret(a);void 0===b?runtime.log('MemberModel sent undefined data for member "'+a+'".'):(null===b&&(b={memberid:a,fullname:"Unknown Identity",color:"black",imageurl:"avatar-joe.png"}),d&&(d.setAvatarImageUrl(b.imageurl),
d.setColor(b.color)),g(a,b.fullname,b.color))}function n(b){var d=b.getMemberId(),e=h.getMemberModel();c.registerCursor(b,r,k);a(d,null);e.getMemberDetailsAndUpdates(d,a);runtime.log("+++ View here +++ eagerly created an Caret for '"+d+"'! +++")}function e(b){var c=!1,d;for(d in t)if(t.hasOwnProperty(d)&&t[d].getEditInfo().getEdits().hasOwnProperty(b)){c=!0;break}c||h.getMemberModel().unsubscribeMemberDetailsUpdates(b,a)}var d,t={},l=void 0!==f.editInfoMarkersInitiallyVisible?Boolean(f.editInfoMarkersInitiallyVisible):
!0,r=void 0!==f.caretAvatarsInitiallyVisible?Boolean(f.caretAvatarsInitiallyVisible):!0,k=void 0!==f.caretBlinksOnRangeSelect?Boolean(f.caretBlinksOnRangeSelect):!0;this.showEditInfoMarkers=function(){l||(l=!0,b(l))};this.hideEditInfoMarkers=function(){l&&(l=!1,b(l))};this.showCaretAvatars=function(){r||(r=!0,p(r))};this.hideCaretAvatars=function(){r&&(r=!1,p(r))};this.getSession=function(){return h};this.getCaret=function(a){return c.getCaret(a)};(function(){var a=h.getOdtDocument(),b=document.getElementsByTagName("head")[0];
a.subscribe(ops.OdtDocument.signalCursorAdded,n);a.subscribe(ops.OdtDocument.signalCursorRemoved,e);a.subscribe(ops.OdtDocument.signalParagraphChanged,function(a){var b=a.paragraphElement,c=a.memberId;a=a.timeStamp;var d,e="",f=b.getElementsByTagNameNS("urn:webodf:names:editinfo","editinfo")[0];f?(e=f.getAttributeNS("urn:webodf:names:editinfo","id"),d=t[e]):(e=Math.random().toString(),d=new ops.EditInfo(b,h.getOdtDocument()),d=new gui.EditInfoMarker(d,l),f=b.getElementsByTagNameNS("urn:webodf:names:editinfo",
"editinfo")[0],f.setAttributeNS("urn:webodf:names:editinfo","id",e),t[e]=d);d.addEdit(c,new Date(a))});d=document.createElementNS(b.namespaceURI,"style");d.type="text/css";d.media="screen, print, handheld, projection";d.appendChild(document.createTextNode("@namespace editinfo url(urn:webodf:names:editinfo);"));d.appendChild(document.createTextNode("@namespace dc url(http://purl.org/dc/elements/1.1/);"));b.appendChild(d)})()}}();
// Input 72
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("gui.Caret");
gui.CaretManager=function(f){function h(a){return e.hasOwnProperty(a)?e[a]:null}function c(){return f.getSession().getOdtDocument().getOdfCanvas().getElement()}function g(a){a===f.getInputMemberId()&&c().removeAttribute("tabindex");delete e[a]}function b(a){a=a.getMemberId();a===f.getInputMemberId()&&(a=h(a))&&a.refreshCursorBlinking()}function p(a){a.memberId===f.getInputMemberId()&&(a=h(a.memberId))&&a.ensureVisible()}function a(){var a=h(f.getInputMemberId());a&&a.setFocus()}function n(){var a=
h(f.getInputMemberId());a&&a.removeFocus()}var e={};this.registerCursor=function(a,b,g){var h=a.getMemberId(),k=c();b=new gui.Caret(a,b,g);e[h]=b;h===f.getInputMemberId()&&(runtime.log("Starting to track input on new cursor of "+h),a.handleUpdate=b.ensureVisible,k.setAttribute("tabindex",0),k.focus());return b};this.getCaret=h;this.getCarets=function(){return Object.keys(e).map(function(a){return e[a]})};(function(){var d=f.getSession().getOdtDocument(),e=c();d.subscribe(ops.OdtDocument.signalParagraphChanged,
p);d.subscribe(ops.OdtDocument.signalCursorMoved,b);d.subscribe(ops.OdtDocument.signalCursorRemoved,g);e.onfocus=a;e.onblur=n})()};
// Input 73
runtime.loadClass("xmldom.XPath");runtime.loadClass("odf.Namespaces");
gui.PresenterUI=function(){var f=new xmldom.XPath,h=runtime.getWindow();return function(c){var g=this;g.setInitialSlideMode=function(){g.startSlideMode("single")};g.keyDownHandler=function(b){if(!b.target.isContentEditable&&"input"!==b.target.nodeName)switch(b.keyCode){case 84:g.toggleToolbar();break;case 37:case 8:g.prevSlide();break;case 39:case 32:g.nextSlide();break;case 36:g.firstSlide();break;case 35:g.lastSlide()}};g.root=function(){return g.odf_canvas.odfContainer().rootElement};g.firstSlide=
function(){g.slideChange(function(b,c){return 0})};g.lastSlide=function(){g.slideChange(function(b,c){return c-1})};g.nextSlide=function(){g.slideChange(function(b,c){return b+1<c?b+1:-1})};g.prevSlide=function(){g.slideChange(function(b,c){return 1>b?-1:b-1})};g.slideChange=function(b){var c=g.getPages(g.odf_canvas.odfContainer().rootElement),a=-1,f=0;c.forEach(function(b){b=b[1];b.hasAttribute("slide_current")&&(a=f,b.removeAttribute("slide_current"));f+=1});b=b(a,c.length);-1===b&&(b=a);c[b][1].setAttribute("slide_current",
"1");document.getElementById("pagelist").selectedIndex=b;"cont"===g.slide_mode&&h.scrollBy(0,c[b][1].getBoundingClientRect().top-30)};g.selectSlide=function(b){g.slideChange(function(c,a){return b>=a||0>b?-1:b})};g.scrollIntoContView=function(b){var c=g.getPages(g.odf_canvas.odfContainer().rootElement);0!==c.length&&h.scrollBy(0,c[b][1].getBoundingClientRect().top-30)};g.getPages=function(b){b=b.getElementsByTagNameNS(odf.Namespaces.drawns,"page");var c=[],a;for(a=0;a<b.length;a+=1)c.push([b[a].getAttribute("draw:name"),
b[a]]);return c};g.fillPageList=function(b,c){for(var a=g.getPages(b),h,e,d;c.firstChild;)c.removeChild(c.firstChild);for(h=0;h<a.length;h+=1)e=document.createElement("option"),d=f.getODFElementsWithXPath(a[h][1],'./draw:frame[@presentation:class="title"]//draw:text-box/text:p',xmldom.XPath),d=0<d.length?d[0].textContent:a[h][0],e.textContent=h+1+": "+d,c.appendChild(e)};g.startSlideMode=function(b){var c=document.getElementById("pagelist"),a=g.odf_canvas.slidevisibilitycss().sheet;for(g.slide_mode=
b;0<a.cssRules.length;)a.deleteRule(0);g.selectSlide(0);"single"===g.slide_mode?(a.insertRule("draw|page { position:fixed; left:0px;top:30px; z-index:1; }",0),a.insertRule("draw|page[slide_current]  { z-index:2;}",1),a.insertRule("draw|page  { -webkit-transform: scale(1);}",2),g.fitToWindow(),h.addEventListener("resize",g.fitToWindow,!1)):"cont"===g.slide_mode&&h.removeEventListener("resize",g.fitToWindow,!1);g.fillPageList(g.odf_canvas.odfContainer().rootElement,c)};g.toggleToolbar=function(){var b,
c,a;b=g.odf_canvas.slidevisibilitycss().sheet;c=-1;for(a=0;a<b.cssRules.length;a+=1)if(".toolbar"===b.cssRules[a].cssText.substring(0,8)){c=a;break}-1<c?b.deleteRule(c):b.insertRule(".toolbar { position:fixed; left:0px;top:-200px; z-index:0; }",0)};g.fitToWindow=function(){var b=g.getPages(g.root()),c=(h.innerHeight-40)/b[0][1].clientHeight,b=(h.innerWidth-10)/b[0][1].clientWidth,c=c<b?c:b,b=g.odf_canvas.slidevisibilitycss().sheet;b.deleteRule(2);b.insertRule("draw|page { \n-moz-transform: scale("+
c+"); \n-moz-transform-origin: 0% 0%; -webkit-transform-origin: 0% 0%; -webkit-transform: scale("+c+"); -o-transform-origin: 0% 0%; -o-transform: scale("+c+"); -ms-transform-origin: 0% 0%; -ms-transform: scale("+c+"); }",2)};g.load=function(b){g.odf_canvas.load(b)};g.odf_element=c;g.odf_canvas=new odf.OdfCanvas(g.odf_element);g.odf_canvas.addListener("statereadychange",g.setInitialSlideMode);g.slide_mode="undefined";document.addEventListener("keydown",g.keyDownHandler,!1)}}();
// Input 74
runtime.loadClass("core.PositionIterator");runtime.loadClass("core.Cursor");
gui.XMLEdit=function(f,h){function c(a,b,c){a.addEventListener?a.addEventListener(b,c,!1):a.attachEvent?a.attachEvent("on"+b,c):a["on"+b]=c}function g(a){a.preventDefault?a.preventDefault():a.returnValue=!1}function b(){var a=f.ownerDocument.defaultView.getSelection();!a||(0>=a.rangeCount||!m)||(a=a.getRangeAt(0),m.setPoint(a.startContainer,a.startOffset))}function p(){var a=f.ownerDocument.defaultView.getSelection(),b,c;a.removeAllRanges();m&&m.node()&&(b=m.node(),c=b.ownerDocument.createRange(),
c.setStart(b,m.position()),c.collapse(!0),a.addRange(c))}function a(a){var c=a.charCode||a.keyCode;if(m=null,m&&37===c)b(),m.stepBackward(),p();else if(16<=c&&20>=c||33<=c&&40>=c)return;g(a)}function n(a){g(a)}function e(a){for(var b=a.firstChild;b&&b!==a;)b.nodeType===Node.ELEMENT_NODE&&e(b),b=b.nextSibling||b.parentNode;var c,d,f,b=a.attributes;c="";for(f=b.length-1;0<=f;f-=1)d=b.item(f),c=c+" "+d.nodeName+'="'+d.nodeValue+'"';a.setAttribute("customns_name",a.nodeName);a.setAttribute("customns_atts",
c);b=a.firstChild;for(d=/^\s*$/;b&&b!==a;)c=b,b=b.nextSibling||b.parentNode,c.nodeType===Node.TEXT_NODE&&d.test(c.nodeValue)&&c.parentNode.removeChild(c)}function d(a,b){for(var c=a.firstChild,e,f,g;c&&c!==a;){if(c.nodeType===Node.ELEMENT_NODE)for(d(c,b),e=c.attributes,g=e.length-1;0<=g;g-=1)f=e.item(g),"http://www.w3.org/2000/xmlns/"!==f.namespaceURI||b[f.nodeValue]||(b[f.nodeValue]=f.localName);c=c.nextSibling||c.parentNode}}function t(){var a=f.ownerDocument.createElement("style"),b;b={};d(f,b);
var c={},e,g,k=0;for(e in b)if(b.hasOwnProperty(e)&&e){g=b[e];if(!g||c.hasOwnProperty(g)||"xmlns"===g){do g="ns"+k,k+=1;while(c.hasOwnProperty(g));b[e]=g}c[g]=!0}a.type="text/css";b="@namespace customns url(customns);\n"+l;a.appendChild(f.ownerDocument.createTextNode(b));h=h.parentNode.replaceChild(a,h)}var l,r,k,m=null;f.id||(f.id="xml"+String(Math.random()).substring(2));r="#"+f.id+" ";l=r+"*,"+r+":visited, "+r+":link {display:block; margin: 0px; margin-left: 10px; font-size: medium; color: black; background: white; font-variant: normal; font-weight: normal; font-style: normal; font-family: sans-serif; text-decoration: none; white-space: pre-wrap; height: auto; width: auto}\n"+
r+":before {color: blue; content: '<' attr(customns_name) attr(customns_atts) '>';}\n"+r+":after {color: blue; content: '</' attr(customns_name) '>';}\n"+r+"{overflow: auto;}\n";(function(b){c(b,"click",n);c(b,"keydown",a);c(b,"drop",g);c(b,"dragend",g);c(b,"beforepaste",g);c(b,"paste",g)})(f);this.updateCSS=t;this.setXML=function(a){a=a.documentElement||a;k=a=f.ownerDocument.importNode(a,!0);for(e(a);f.lastChild;)f.removeChild(f.lastChild);f.appendChild(a);t();m=new core.PositionIterator(a)};this.getXML=
function(){return k}};
// Input 75
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
gui.UndoManager=function(){};gui.UndoManager.prototype.subscribe=function(f,h){};gui.UndoManager.prototype.unsubscribe=function(f,h){};gui.UndoManager.prototype.setOdtDocument=function(f){};gui.UndoManager.prototype.saveInitialState=function(){};gui.UndoManager.prototype.resetInitialState=function(){};gui.UndoManager.prototype.setPlaybackFunction=function(f){};gui.UndoManager.prototype.hasUndoStates=function(){};gui.UndoManager.prototype.hasRedoStates=function(){};
gui.UndoManager.prototype.moveForward=function(f){};gui.UndoManager.prototype.moveBackward=function(f){};gui.UndoManager.prototype.onOperationExecuted=function(f){};gui.UndoManager.signalUndoStackChanged="undoStackChanged";gui.UndoManager.signalUndoStateCreated="undoStateCreated";gui.UndoManager.signalUndoStateModified="undoStateModified";(function(){return gui.UndoManager})();
// Input 76
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
gui.UndoStateRules=function(){function f(c){return c.spec().optype}function h(c){switch(f(c)){case "MoveCursor":case "AddCursor":case "RemoveCursor":return!1;default:return!0}}this.getOpType=f;this.isEditOperation=h;this.isPartOfOperationSet=function(c,g){if(h(c)){if(0===g.length)return!0;var b;if(b=h(g[g.length-1]))a:{b=g.filter(h);var p=f(c),a;b:switch(p){case "RemoveText":case "InsertText":a=!0;break b;default:a=!1}if(a&&p===f(b[0])){if(1===b.length){b=!0;break a}p=b[b.length-2].spec().position;
b=b[b.length-1].spec().position;a=c.spec().position;if(b===a-(b-p)){b=!0;break a}}b=!1}return b}return!0}};
// Input 77
/*

 Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.DomUtils");runtime.loadClass("gui.UndoManager");runtime.loadClass("gui.UndoStateRules");
gui.TrivialUndoManager=function(f){function h(){q.emit(gui.UndoManager.signalUndoStackChanged,{undoAvailable:a.hasUndoStates(),redoAvailable:a.hasRedoStates()})}function c(){r!==d&&r!==k[k.length-1]&&k.push(r)}function g(a){var b=a.previousSibling||a.nextSibling;a.parentNode.removeChild(a);n.normalizeTextNodes(b)}function b(a){return Object.keys(a).map(function(b){return a[b]})}function p(a){function c(a){var b=a.spec();if(f[b.memberid])switch(b.optype){case "AddCursor":d[b.memberid]||(d[b.memberid]=
a,delete f[b.memberid],g-=1);break;case "MoveCursor":e[b.memberid]||(e[b.memberid]=a)}}var d={},e={},f={},g,k=a.pop();l.getCursors().forEach(function(a){f[a.getMemberId()]=!0});for(g=Object.keys(f).length;k&&0<g;)k.reverse(),k.forEach(c),k=a.pop();return b(d).concat(b(e))}var a=this,n=new core.DomUtils,e,d=[],t,l,r=[],k=[],m=[],q=new core.EventNotifier([gui.UndoManager.signalUndoStackChanged,gui.UndoManager.signalUndoStateCreated,gui.UndoManager.signalUndoStateModified,gui.TrivialUndoManager.signalDocumentRootReplaced]),
w=f||new gui.UndoStateRules;this.subscribe=function(a,b){q.subscribe(a,b)};this.unsubscribe=function(a,b){q.unsubscribe(a,b)};this.hasUndoStates=function(){return 0<k.length};this.hasRedoStates=function(){return 0<m.length};this.setOdtDocument=function(a){l=a};this.resetInitialState=function(){k.length=0;m.length=0;d.length=0;r.length=0;e=null;h()};this.saveInitialState=function(){var a=l.getOdfCanvas().odfContainer(),b=l.getOdfCanvas().getAnnotationManager();b&&b.forgetAnnotations();e=a.rootElement.cloneNode(!0);
l.getOdfCanvas().refreshAnnotations();a=e;n.getElementsByTagNameNS(a,"urn:webodf:names:cursor","cursor").forEach(g);n.getElementsByTagNameNS(a,"urn:webodf:names:cursor","anchor").forEach(g);c();k.unshift(d);r=d=p(k);k.length=0;m.length=0;h()};this.setPlaybackFunction=function(a){t=a};this.onOperationExecuted=function(a){m.length=0;w.isEditOperation(a)&&r===d||!w.isPartOfOperationSet(a,r)?(c(),r=[a],k.push(r),q.emit(gui.UndoManager.signalUndoStateCreated,{operations:r}),h()):(r.push(a),q.emit(gui.UndoManager.signalUndoStateModified,
{operations:r}))};this.moveForward=function(a){for(var b=0,c;a&&m.length;)c=m.pop(),k.push(c),c.forEach(t),a-=1,b+=1;b&&(r=k[k.length-1],h());return b};this.moveBackward=function(a){for(var b=l.getOdfCanvas(),c=b.odfContainer(),f=0;a&&k.length;)m.push(k.pop()),a-=1,f+=1;f&&(c.setRootElement(e.cloneNode(!0)),b.setOdfContainer(c,!0),q.emit(gui.TrivialUndoManager.signalDocumentRootReplaced,{}),l.getCursors().forEach(function(a){l.removeCursor(a.getMemberId())}),d.forEach(t),k.forEach(function(a){a.forEach(t)}),
b.refreshCSS(),r=k[k.length-1]||d,h());return f}};gui.TrivialUndoManager.signalDocumentRootReplaced="documentRootReplaced";(function(){return gui.TrivialUndoManager})();
// Input 78
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("core.EventNotifier");runtime.loadClass("odf.OdfUtils");runtime.loadClass("gui.SelectionMover");runtime.loadClass("gui.StyleHelper");runtime.loadClass("core.PositionFilterChain");
ops.OdtDocument=function(f){function h(){var a=f.odfContainer().getContentElement(),b=a&&a.localName;runtime.assert("text"===b,"Unsupported content element type '"+b+"'for OdtDocument");return a}function c(a){function b(a){for(;!(a.namespaceURI===odf.Namespaces.officens&&"text"===a.localName||a.namespaceURI===odf.Namespaces.officens&&"annotation"===a.localName);)a=a.parentNode;return a}this.acceptPosition=function(c){c=c.container();var d=e[a].getNode();return b(c)===b(d)?t:l}}function g(a){var b=
gui.SelectionMover.createPositionIterator(h());for(a+=1;0<a&&b.nextPosition();)1===r.acceptPosition(b)&&(a-=1);return b}function b(a){return n.getParagraphElement(a)}function p(a){return f.getFormatting().getStyleElement(a,"paragraph")}var a=this,n,e={},d=new core.EventNotifier([ops.OdtDocument.signalCursorAdded,ops.OdtDocument.signalCursorRemoved,ops.OdtDocument.signalCursorMoved,ops.OdtDocument.signalParagraphChanged,ops.OdtDocument.signalParagraphStyleModified,ops.OdtDocument.signalStyleCreated,
ops.OdtDocument.signalStyleDeleted,ops.OdtDocument.signalTableAdded,ops.OdtDocument.signalOperationExecuted,ops.OdtDocument.signalUndoStackChanged]),t=core.PositionFilter.FilterResult.FILTER_ACCEPT,l=core.PositionFilter.FilterResult.FILTER_REJECT,r;this.getIteratorAtPosition=g;this.upgradeWhitespacesAtPosition=function(a){a=g(a);var b,c,d;a.previousPosition();a.previousPosition();for(d=-1;1>=d;d+=1){b=a.container();c=a.unfilteredDomOffset();if(b.nodeType===Node.TEXT_NODE&&" "===b.data[c]&&n.isSignificantWhitespace(b,
c)){runtime.assert(" "===b.data[c],"upgradeWhitespaceToElement: textNode.data[offset] should be a literal space");var e=b.ownerDocument.createElementNS("urn:oasis:names:tc:opendocument:xmlns:text:1.0","text:s");e.appendChild(b.ownerDocument.createTextNode(" "));b.deleteData(c,1);0<c&&(b=b.splitText(c));b.parentNode.insertBefore(e,b);b=e;a.moveToEndOfNode(b)}a.nextPosition()}};this.getParagraphStyleElement=p;this.getParagraphElement=b;this.getParagraphStyleAttributes=function(a){return(a=p(a))?f.getFormatting().getInheritedStyleAttributes(a):
null};this.getPositionInTextNode=function(b,c){var d=gui.SelectionMover.createPositionIterator(h()),f=null,g,l=0,n=null,p=b;runtime.assert(0<=b,"position must be >= 0");1===r.acceptPosition(d)?(g=d.container(),g.nodeType===Node.TEXT_NODE&&(f=g,l=0)):b+=1;for(;0<b||null===f;){if(!d.nextPosition())return null;if(1===r.acceptPosition(d))if(b-=1,g=d.container(),g.nodeType===Node.TEXT_NODE)g!==f?(f=g,l=d.domOffset()):l+=1;else if(null!==f){if(0===b){l=f.length;break}f=null}else if(0===b){f=h().ownerDocument.createTextNode("");
g.insertBefore(f,d.rightNode());l=0;break}}if(null===f)return null;if(c&&e[c]&&a.getCursorPosition(c)===p){for(n=e[c].getNode();0===l&&n.nextSibling&&"cursor"===n.nextSibling.localName;)n.parentNode.insertBefore(n,n.nextSibling.nextSibling);n&&0<f.length&&(f=h().ownerDocument.createTextNode(""),l=0,n.parentNode.insertBefore(f,n.nextSibling))}for(;0===l&&(f.previousSibling&&"cursor"===f.previousSibling.localName)&&(g=f.previousSibling,0<f.length&&(f=h().ownerDocument.createTextNode("")),g.parentNode.insertBefore(f,
g),n!==g););for(;f.previousSibling&&f.previousSibling.nodeType===Node.TEXT_NODE;)f.previousSibling.appendData(f.data),l=f.length+f.previousSibling.length,f=f.previousSibling,f.parentNode.removeChild(f.nextSibling);return{textNode:f,offset:l}};this.fixCursorPositions=function(b){var c,d,f,g=new core.PositionFilterChain;g.addFilter("BaseFilter",a.getPositionFilter());for(c in e)e.hasOwnProperty(c)&&(g.addFilter("RootFilter",a.createRootFilter(c)),d=e[c],f=d.getStepCounter(),f.isPositionWalkable(g)?
0===a.getCursorSelection(c).length&&d.move(0):(f=f.countStepsToValidPosition(g),d.move(f),c===b&&a.emit(ops.OdtDocument.signalCursorMoved,d)),g.removeFilter("RootFilter"))};this.getWalkableParagraphLength=function(a){var c=g(0),d=0;c.setUnfilteredPosition(a,0);do{if(b(c.container())!==a)break;1===r.acceptPosition(c)&&(d+=1)}while(c.nextPosition());return d};this.getDistanceFromCursor=function(a,b,c){a=e[a];var d=0;runtime.assert(null!==b&&void 0!==b,"OdtDocument.getDistanceFromCursor called without node");
a&&(a=a.getStepCounter().countStepsToPosition,d=a(b,c,r));return d};this.getCursorPosition=function(b){return-a.getDistanceFromCursor(b,h(),0)};this.getCursorSelection=function(a){var b;a=e[a];var c=0;b=0;a&&(b=a.getStepCounter().countStepsToPosition,c=-b(h(),0,r),b=b(a.getAnchorNode(),0,r));return{position:c+b,length:-b}};this.getPositionFilter=function(){return r};this.getOdfCanvas=function(){return f};this.getRootNode=h;this.getDOM=function(){return h().ownerDocument};this.getCursor=function(a){return e[a]};
this.getCursors=function(){var a=[],b;for(b in e)e.hasOwnProperty(b)&&a.push(e[b]);return a};this.addCursor=function(a){runtime.assert(Boolean(a),"OdtDocument::addCursor without cursor");var b=a.getStepCounter().countForwardSteps(1,r),c=a.getMemberId();runtime.assert(Boolean(c),"OdtDocument::addCursor has cursor without memberid");runtime.assert(!e[c],"OdtDocument::addCursor is adding a duplicate cursor with memberid "+c);a.move(b);e[c]=a};this.removeCursor=function(b){var c=e[b];return c?(c.removeFromOdtDocument(),
delete e[b],a.emit(ops.OdtDocument.signalCursorRemoved,b),!0):!1};this.getMetaData=function(a){for(var b=f.odfContainer().rootElement.firstChild;b&&"meta"!==b.localName;)b=b.nextSibling;for(b=b&&b.firstChild;b&&b.localName!==a;)b=b.nextSibling;for(b=b&&b.firstChild;b&&b.nodeType!==Node.TEXT_NODE;)b=b.nextSibling;return b?b.data:null};this.getFormatting=function(){return f.getFormatting()};this.getTextElements=function(a,b){return n.getTextElements(a,b)};this.getParagraphElements=function(a){return n.getParagraphElements(a)};
this.emit=function(a,b){d.emit(a,b)};this.subscribe=function(a,b){d.subscribe(a,b)};this.unsubscribe=function(a,b){d.unsubscribe(a,b)};this.createRootFilter=function(a){return new c(a)};r=new function(){function a(b,c,d){var e,f;if(c&&(e=n.lookLeftForCharacter(c),1===e||2===e&&(n.scanRightForAnyCharacter(d)||n.scanRightForAnyCharacter(n.nextNode(b)))))return t;e=null===c&&n.isParagraph(b);f=n.lookRightForCharacter(d);if(e)return f?t:n.scanRightForAnyCharacter(d)?l:t;if(!f)return l;c=c||n.previousNode(b);
return n.scanLeftForAnyCharacter(c)?l:t}this.acceptPosition=function(b){var c=b.container(),d=c.nodeType,e,f,g;if(d!==Node.ELEMENT_NODE&&d!==Node.TEXT_NODE)return l;if(d===Node.TEXT_NODE){if(!n.isGroupingElement(c.parentNode)||n.isWithinTrackedChanges(c.parentNode,h()))return l;d=b.unfilteredDomOffset();e=c.data;runtime.assert(d!==e.length,"Unexpected offset.");if(0<d){b=e.substr(d-1,1);if(!n.isODFWhitespace(b))return t;if(1<d)if(b=e.substr(d-2,1),!n.isODFWhitespace(b))f=t;else{if(!n.isODFWhitespace(e.substr(0,
d)))return l}else g=n.previousNode(c),n.scanLeftForNonWhitespace(g)&&(f=t);if(f===t)return n.isTrailingWhitespace(c,d)?l:t;f=e.substr(d,1);return n.isODFWhitespace(f)?l:n.scanLeftForAnyCharacter(n.previousNode(c))?l:t}g=b.leftNode();f=c;c=c.parentNode;f=a(c,g,f)}else!n.isGroupingElement(c)||n.isWithinTrackedChanges(c,h())?f=l:(g=b.leftNode(),f=b.rightNode(),f=a(c,g,f));return f}};n=new odf.OdfUtils};ops.OdtDocument.signalCursorAdded="cursor/added";ops.OdtDocument.signalCursorRemoved="cursor/removed";
ops.OdtDocument.signalCursorMoved="cursor/moved";ops.OdtDocument.signalParagraphChanged="paragraph/changed";ops.OdtDocument.signalTableAdded="table/added";ops.OdtDocument.signalStyleCreated="style/created";ops.OdtDocument.signalStyleDeleted="style/deleted";ops.OdtDocument.signalParagraphStyleModified="paragraphstyle/modified";ops.OdtDocument.signalOperationExecuted="operation/executed";ops.OdtDocument.signalUndoStackChanged="undo/changed";(function(){return ops.OdtDocument})();
// Input 79
/*

 Copyright (C) 2012-2013 KO GmbH <copyright@kogmbh.com>

 @licstart
 The JavaScript code in this page is free software: you can redistribute it
 and/or modify it under the terms of the GNU Affero General Public License
 (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 the License, or (at your option) any later version.  The code is distributed
 WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.

 As additional permission under GNU AGPL version 3 section 7, you
 may distribute non-source (e.g., minimized or compacted) forms of
 that code without the copy of the GNU GPL normally required by
 section 4, provided you include this license notice and a URL
 through which recipients can access the Corresponding Source.

 As a special exception to the AGPL, any HTML file which merely makes function
 calls to this code, and for that purpose includes it by reference shall be
 deemed a separate work for copyright law purposes. In addition, the copyright
 holders of this code give you permission to combine this code with free
 software libraries that are released under the GNU LGPL. You may copy and
 distribute such a system following the terms of the GNU AGPL for this code
 and the LGPL for the libraries. If you modify this code, you may extend this
 exception to your version of the code, but you are not obligated to do so.
 If you do not wish to do so, delete this exception statement from your
 version.

 This license applies to this entire compilation.
 @licend
 @source: http://www.webodf.org/
 @source: http://gitorious.org/webodf/webodf/
*/
runtime.loadClass("ops.TrivialMemberModel");runtime.loadClass("ops.TrivialOperationRouter");runtime.loadClass("ops.OperationFactory");runtime.loadClass("ops.OdtDocument");
ops.Session=function(f){var h=new ops.OperationFactory,c=new ops.OdtDocument(f),g=new ops.TrivialMemberModel,b=null;this.setMemberModel=function(b){g=b};this.setOperationFactory=function(c){h=c;b&&b.setOperationFactory(h)};this.setOperationRouter=function(f){b=f;f.setPlaybackFunction(function(a){a.execute(c);c.emit(ops.OdtDocument.signalOperationExecuted,a)});f.setOperationFactory(h)};this.getMemberModel=function(){return g};this.getOperationFactory=function(){return h};this.getOdtDocument=function(){return c};
this.enqueue=function(c){b.push(c)};this.setOperationRouter(new ops.TrivialOperationRouter)};
// Input 80
var webodf_css="@namespace draw url(urn:oasis:names:tc:opendocument:xmlns:drawing:1.0);\n@namespace fo url(urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0);\n@namespace office url(urn:oasis:names:tc:opendocument:xmlns:office:1.0);\n@namespace presentation url(urn:oasis:names:tc:opendocument:xmlns:presentation:1.0);\n@namespace style url(urn:oasis:names:tc:opendocument:xmlns:style:1.0);\n@namespace svg url(urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0);\n@namespace table url(urn:oasis:names:tc:opendocument:xmlns:table:1.0);\n@namespace text url(urn:oasis:names:tc:opendocument:xmlns:text:1.0);\n@namespace runtimens url(urn:webodf); /* namespace for runtime only */\n@namespace cursor url(urn:webodf:names:cursor);\n@namespace editinfo url(urn:webodf:names:editinfo);\n@namespace annotation url(urn:webodf:names:annotation);\n@namespace dc url(http://purl.org/dc/elements/1.1/);\n\noffice|document > *, office|document-content > * {\n  display: none;\n}\noffice|body, office|document {\n  display: inline-block;\n  position: relative;\n}\n\ntext|p, text|h {\n  display: block;\n  padding: 0;\n  margin: 0;\n  line-height: normal;\n  position: relative;\n  min-height: 1.3em; /* prevent empty paragraphs and headings from collapsing if they are empty */\n}\n*[runtimens|containsparagraphanchor] {\n  position: relative;\n}\ntext|s {\n    white-space: pre;\n}\ntext|tab {\n  display: inline;\n  white-space: pre;\n}\ntext|line-break {\n  content: \" \";\n  display: block;\n}\ntext|tracked-changes {\n  /*Consumers that do not support change tracking, should ignore changes.*/\n  display: none;\n}\noffice|binary-data {\n  display: none;\n}\noffice|text {\n  display: block;\n  text-align: left;\n  overflow: visible;\n  word-wrap: break-word;\n}\n\noffice|text::selection {\n    /** Let's not draw selection highlight that overflows into the office|text\n     * node when selecting content across several paragraphs\n     */\n    background: transparent;\n}\noffice|text * draw|text-box {\n    /** only for text documents */\n    display: block;\n    border: 1px solid #d3d3d3;\n}\noffice|spreadsheet {\n  display: block;\n  border-collapse: collapse;\n  empty-cells: show;\n  font-family: sans-serif;\n  font-size: 10pt;\n  text-align: left;\n  page-break-inside: avoid;\n  overflow: hidden;\n}\noffice|presentation {\n  display: inline-block;\n  text-align: left;\n}\n#shadowContent {\n  display: inline-block;\n  text-align: left;\n}\ndraw|page {\n  display: block;\n  position: relative;\n  overflow: hidden;\n}\npresentation|notes, presentation|footer-decl, presentation|date-time-decl {\n    display: none;\n}\n@media print {\n  draw|page {\n    border: 1pt solid black;\n    page-break-inside: avoid;\n  }\n  presentation|notes {\n    /*TODO*/\n  }\n}\noffice|spreadsheet text|p {\n  border: 0px;\n  padding: 1px;\n  margin: 0px;\n}\noffice|spreadsheet table|table {\n  margin: 3px;\n}\noffice|spreadsheet table|table:after {\n  /* show sheet name the end of the sheet */\n  /*content: attr(table|name);*/ /* gives parsing error in opera */\n}\noffice|spreadsheet table|table-row {\n  counter-increment: row;\n}\noffice|spreadsheet table|table-row:before {\n  width: 3em;\n  background: #cccccc;\n  border: 1px solid black;\n  text-align: center;\n  content: counter(row);\n  display: table-cell;\n}\noffice|spreadsheet table|table-cell {\n  border: 1px solid #cccccc;\n}\ntable|table {\n  display: table;\n}\ndraw|frame table|table {\n  width: 100%;\n  height: 100%;\n  background: white;\n}\ntable|table-header-rows {\n  display: table-header-group;\n}\ntable|table-row {\n  display: table-row;\n}\ntable|table-column {\n  display: table-column;\n}\ntable|table-cell {\n  width: 0.889in;\n  display: table-cell;\n  word-break: break-all; /* prevent long words from extending out the table cell */\n}\ndraw|frame {\n  display: block;\n}\ndraw|image {\n  display: block;\n  width: 100%;\n  height: 100%;\n  top: 0px;\n  left: 0px;\n  background-repeat: no-repeat;\n  background-size: 100% 100%;\n  -moz-background-size: 100% 100%;\n}\n/* only show the first image in frame */\ndraw|frame > draw|image:nth-of-type(n+2) {\n  display: none;\n}\ntext|list:before {\n    display: none;\n    content:\"\";\n}\ntext|list {\n    counter-reset: list;\n}\ntext|list-item {\n    display: block;\n}\ntext|number {\n    display:none;\n}\n\ntext|a {\n    color: blue;\n    text-decoration: underline;\n    cursor: pointer;\n}\ntext|note-citation {\n    vertical-align: super;\n    font-size: smaller;\n}\ntext|note-body {\n    display: none;\n}\ntext|note:hover text|note-citation {\n    background: #dddddd;\n}\ntext|note:hover text|note-body {\n    display: block;\n    left:1em;\n    max-width: 80%;\n    position: absolute;\n    background: #ffffaa;\n}\nsvg|title, svg|desc {\n    display: none;\n}\nvideo {\n    width: 100%;\n    height: 100%\n}\n\n/* below set up the cursor */\ncursor|cursor {\n    display: inline;\n    width: 0px;\n    height: 1em;\n    /* making the position relative enables the avatar to use\n       the cursor as reference for its absolute position */\n    position: relative;\n    z-index: 1;\n}\ncursor|cursor > span {\n    display: inline;\n    position: absolute;\n    top: 5%; /* push down the caret; 0px can do the job, 5% looks better, 10% is a bit over */\n    height: 1em;\n    border-left: 2px solid black;\n    outline: none;\n}\n\ncursor|cursor > div {\n    padding: 3px;\n    box-shadow: 0px 0px 5px rgba(50, 50, 50, 0.75);\n    border: none !important;\n    border-radius: 5px;\n    opacity: 0.3;\n}\n\ncursor|cursor > div > img {\n    border-radius: 5px;\n}\n\ncursor|cursor > div.active {\n    opacity: 0.8;\n}\n\ncursor|cursor > div:after {\n    content: ' ';\n    position: absolute;\n    width: 0px;\n    height: 0px;\n    border-style: solid;\n    border-width: 8.7px 5px 0 5px;\n    border-color: black transparent transparent transparent;\n\n    top: 100%;\n    left: 43%;\n}\n\n\n.editInfoMarker {\n    position: absolute;\n    width: 10px;\n    height: 100%;\n    left: -20px;\n    opacity: 0.8;\n    top: 0;\n    border-radius: 5px;\n    background-color: transparent;\n    box-shadow: 0px 0px 5px rgba(50, 50, 50, 0.75);\n}\n.editInfoMarker:hover {\n    box-shadow: 0px 0px 8px rgba(0, 0, 0, 1);\n}\n\n.editInfoHandle {\n    position: absolute;\n    background-color: black;\n    padding: 5px;\n    border-radius: 5px;\n    opacity: 0.8;\n    box-shadow: 0px 0px 5px rgba(50, 50, 50, 0.75);\n    bottom: 100%;\n    margin-bottom: 10px;\n    z-index: 3;\n    left: -25px;\n}\n.editInfoHandle:after {\n    content: ' ';\n    position: absolute;\n    width: 0px;\n    height: 0px;\n    border-style: solid;\n    border-width: 8.7px 5px 0 5px;\n    border-color: black transparent transparent transparent;\n\n    top: 100%;\n    left: 5px;\n}\n.editInfo {\n    font-family: sans-serif;\n    font-weight: normal;\n    font-style: normal;\n    text-decoration: none;\n    color: white;\n    width: 100%;\n    height: 12pt;\n}\n.editInfoColor {\n    float: left;\n    width: 10pt;\n    height: 10pt;\n    border: 1px solid white;\n}\n.editInfoAuthor {\n    float: left;\n    margin-left: 5pt;\n    font-size: 10pt;\n    text-align: left;\n    height: 12pt;\n    line-height: 12pt;\n}\n.editInfoTime {\n    float: right;\n    margin-left: 30pt;\n    font-size: 8pt;\n    font-style: italic;\n    color: yellow;\n    height: 12pt;\n    line-height: 12pt;\n}\n\n.annotationWrapper {\n    display: inline;\n    position: relative;\n}\n\n.annotationRemoveButton:before {\n    content: '\u00d7';\n    color: white;\n    padding: 5px;\n    line-height: 1em;\n}\n\n.annotationRemoveButton {\n    width: 20px;\n    height: 20px;\n    border-radius: 10px;\n    background-color: black;\n    box-shadow: 0px 0px 5px rgba(50, 50, 50, 0.75);\n    position: absolute;\n    top: -10px;\n    left: -10px;\n    z-index: 3;\n    text-align: center;\n    font-family: sans-serif;\n    font-style: normal;\n    font-weight: normal;\n    text-decoration: none;\n    font-size: 15px;\n}\n.annotationRemoveButton:hover {\n    cursor: pointer;\n    box-shadow: 0px 0px 5px rgba(0, 0, 0, 1);\n}\n\n.annotationNote {\n    width: 4cm;\n    position: absolute;\n    display: inline;\n    z-index: 10;\n}\n.annotationNote > office|annotation {\n    display: block;\n}\n\n.annotationConnector {\n    position: absolute;\n    display: inline;\n    z-index: 2;\n    border-top: 1px dashed brown;\n}\n.annotationConnector.angular {\n    -moz-transform-origin: left top;\n    -webkit-transform-origin: left top;\n    -ms-transform-origin: left top;\n    transform-origin: left top;\n}\n.annotationConnector.horizontal {\n    left: 0;\n}\n.annotationConnector.horizontal:before {\n    content: '';\n    display: inline;\n    position: absolute;\n    width: 0px;\n    height: 0px;\n    border-style: solid;\n    border-width: 8.7px 5px 0 5px;\n    border-color: brown transparent transparent transparent;\n    top: -1px;\n    left: -5px;\n}\n\noffice|annotation {\n    width: 100%;\n    height: 100%;\n    display: none;\n    background: rgb(198, 238, 184);\n    background: -moz-linear-gradient(90deg, rgb(198, 238, 184) 30%, rgb(180, 196, 159) 100%);\n    background: -webkit-linear-gradient(90deg, rgb(198, 238, 184) 30%, rgb(180, 196, 159) 100%);\n    background: -o-linear-gradient(90deg, rgb(198, 238, 184) 30%, rgb(180, 196, 159) 100%);\n    background: -ms-linear-gradient(90deg, rgb(198, 238, 184) 30%, rgb(180, 196, 159) 100%);\n    background: linear-gradient(180deg, rgb(198, 238, 184) 30%, rgb(180, 196, 159) 100%);\n    box-shadow: 0 3px 4px -3px #ccc;\n}\n\noffice|annotation > dc|creator {\n    display: block;\n    font-size: 10pt;\n    font-weight: normal;\n    font-style: normal;\n    font-family: sans-serif;\n    color: white;\n    background-color: brown;\n    padding: 4px;\n}\noffice|annotation > dc|date {\n    display: block;\n    font-size: 10pt;\n    font-weight: normal;\n    font-style: normal;\n    font-family: sans-serif;\n    border: 4px solid transparent;\n}\noffice|annotation > text|list {\n    display: block;\n    padding: 5px;\n}\n\n/* This is very temporary CSS. This must go once\n * we start bundling webodf-default ODF styles for annotations.\n */\noffice|annotation text|p {\n    font-size: 10pt;\n    color: black;\n    font-weight: normal;\n    font-style: normal;\n    text-decoration: none;\n    font-family: sans-serif;\n}\n\ndc|*::selection {\n    background: transparent;\n}\ndc|*::-moz-selection {\n    background: transparent;\n}\n\n#annotationsPane {\n    background-color: #EAEAEA;\n    width: 4cm;\n    height: 100%;\n    display: none;\n    position: absolute;\n    outline: 1px solid #ccc;\n}\n\n.annotationHighlight {\n    background-color: yellow;\n    position: relative;\n}\n";
