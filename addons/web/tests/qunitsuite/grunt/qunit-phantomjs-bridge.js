/*
 * grunt
 * http://gruntjs.com/
 *
 * Copyright (c) 2012 "Cowboy" Ben Alman
 * Licensed under the MIT license.
 * http://benalman.com/about/license/
 */

/*global QUnit:true, alert:true*/

'use strict';

// Don't re-order tests.
QUnit.config.reorder = false;
// Run tests serially, not in parallel.
QUnit.config.autorun = false;

// Send messages to the parent PhantomJS process via alert! Good times!!
function sendMessage() {
  var args = [].slice.call(arguments);
  alert(JSON.stringify(args));
}

// These methods connect QUnit to PhantomJS.
QUnit.log(function(obj) {
  // What is this I don’t even
  if (obj.message === '[object Object], undefined:undefined') { return; }
  // Parse some stuff before sending it.
  var actual = QUnit.jsDump.parse(obj.actual);
  var expected = QUnit.jsDump.parse(obj.expected);
  // Send it.
  sendMessage('qunit.log', obj.result, actual, expected, obj.message, obj.source);
});

QUnit.testStart(function(obj) {
  sendMessage('qunit.testStart', obj.name);
});

QUnit.testDone(function(obj) {
  sendMessage('qunit.testDone', obj.name, obj.failed, obj.passed, obj.total);
});

QUnit.moduleStart(function(obj) {
  sendMessage('qunit.moduleStart', obj.name);
});

QUnit.moduleDone(function(obj) {
  sendMessage('qunit.moduleDone', obj.name, obj.failed, obj.passed, obj.total);
});

QUnit.begin(function() {
  sendMessage('qunit.begin');
});

QUnit.done(function(obj) {
  sendMessage('qunit.done', obj.failed, obj.passed, obj.total, obj.runtime);
});

// PhantomJS (up to and including 1.7) uses a version of webkit so old
// it does not have Function.prototype.bind:
// http://code.google.com/p/phantomjs/issues/detail?id=522

// Use moz polyfill:
// https://developer.mozilla.org/en-US/docs/JavaScript/Reference/Global_Objects/Function/bind#Compatibility
if (!Function.prototype.bind) {
  Function.prototype.bind = function (oThis) {
    if (typeof this !== "function") {
      // closest thing possible to the ECMAScript 5 internal IsCallable function
      throw new TypeError("Function.prototype.bind - what is trying to be bound is not callable");
    }

    var aArgs = Array.prototype.slice.call(arguments, 1),
        fToBind = this,
        fNOP = function () {},
        fBound = function () {
          return fToBind.apply(this instanceof fNOP && oThis
                                 ? this
                                 : oThis,
                               aArgs.concat(Array.prototype.slice.call(arguments)));
        };

    fNOP.prototype = this.prototype;
    fBound.prototype = new fNOP();

    return fBound;
  };
}
