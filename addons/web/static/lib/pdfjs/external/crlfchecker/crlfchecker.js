/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* jshint node:true */
/* globals cat, echo, exit, ls */

'use strict';

function checkIfCrlfIsPresent(files) {
  var failed = [];

  (ls(files)).forEach(function checkCrlf(file) {
    if ((cat(file)).match(/.*\r.*/)) {
      failed.push(file);
    }
  });

  if (failed.length) {
    var errorMessage =
      'Please remove carriage return\'s from\n' + failed.join('\n') + '\n' +
      'Also check your setting for: git config core.autocrlf.';

    echo();
    echo(errorMessage);
    exit(1);
  }
}

exports.checkIfCrlfIsPresent = checkIfCrlfIsPresent;

