/*
 * grunt
 * http://gruntjs.com/
 *
 * Copyright (c) 2012 "Cowboy" Ben Alman
 * Licensed under the MIT license.
 * http://benalman.com/about/license/
 */

/*global phantom:true*/

'use strict';

var fs = require('fs');

// The page .html file to load.
var url = phantom.args[0];
// Extra, optionally overridable stuff.
var options = JSON.parse(phantom.args[1] || {});

// Default options.
if (!options.timeout) { options.timeout = 5000; }

// Keep track of the last time a client message was sent.
var last = new Date();

// Messages are sent to the parent by appending them to the tempfile.
var sendMessage = function(arg) {
  var args = Array.isArray(arg) ? arg : [].slice.call(arguments);
  last = new Date();
  console.log(JSON.stringify(args));
};

// This allows grunt to abort if the PhantomJS version isn't adequate.
sendMessage('private', 'version', phantom.version);

// Abort if the page doesn't send any messages for a while.
setInterval(function() {
  if (new Date() - last > options.timeout) {
    sendMessage('fail.timeout');
    phantom.exit();
  }
}, 100);

// Create a new page.
var page = require('webpage').create();

// The client page must send its messages via alert(jsonstring).
page.onAlert = function(args) {
  sendMessage(JSON.parse(args));
};

// Keep track if the client-side helper script already has been injected.
var injected;
page.onUrlChanged = function(newUrl) {
  injected = false;
  sendMessage('onUrlChanged', newUrl);
};

// Relay console logging messages.
page.onConsoleMessage = function(message) {
  sendMessage('console', message);
};

// For debugging.
page.onResourceRequested = function(request) {
  sendMessage('onResourceRequested', request.url);
};

page.onResourceReceived = function(request) {
  if (request.stage === 'end') {
    sendMessage('onResourceReceived', request.url);
  }
};

// Run when the page has finished loading.
page.onLoadFinished = function(status) {
  // The window has loaded.
  sendMessage('onLoadFinished', status);
  if (status === 'success') {
    if (options.inject && !injected) {
      // Inject client-side helper script, but only if it has not yet been
      // injected.
      sendMessage('inject', options.inject);
      page.injectJs(options.inject);
    }
  } else {
    // File loading failure.
    sendMessage('fail.load', url);
    phantom.exit();
  }
};

// Actually load url.
page.open(url);
