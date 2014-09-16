/*jshint node:true */


// Module exports
exports = module.exports = setup;

// Module dependencies
var http = require("http");
var send = require("send");


var root = __dirname;
var swf = "/ZeroClipboard.swf";

function setup() {
  return http.createServer(onReq);
}

function onReq(req, res) {
  send(req, swf)
    .root(root)
    .on("error", onError)
    .pipe(res);
}

function onError(err) {
  res.statusCode = err.status || 500;
  res.end(err.message);
}
