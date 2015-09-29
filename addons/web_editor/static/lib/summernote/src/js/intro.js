/**
 * Super simple wysiwyg editor on Bootstrap v@VERSION
 * http://hackerwins.github.io/summernote/
 *
 * summernote.js
 * Copyright 2013-2014 Alan Hong. and other contributors
 * summernote may be freely distributed under the MIT license./
 *
 * Date: @DATE
 */
(function (factory) {
  /* global define */
  if (typeof define === 'function' && define.amd) {
    // AMD. Register as an anonymous module.
    define(['jquery'], factory);
  } else {
    // Browser globals: jQuery
    factory(window.jQuery);
  }
}(function ($) {
  'use strict';
