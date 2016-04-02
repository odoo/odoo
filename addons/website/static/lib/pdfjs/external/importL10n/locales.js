/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2012 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/* jshint node:true */

'use strict';

var fs = require('fs');
var http = require('http');
var path = require('path');

// Defines all languages that have a translation at mozilla-aurora.
// This is used in make.js for the importl10n command.
var langCodes = [
  'ach', 'af', 'ak', 'an', 'ar', 'as', 'ast', 'az', 'be', 'bg',
  'bn-BD', 'bn-IN', 'br', 'bs', 'ca', 'cs', 'csb', 'cy', 'da',
  'de', 'el', 'en-GB', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
  'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE',
  'gd', 'gl', 'gu-IN', 'he', 'hi-IN', 'hr', 'hu', 'hy-AM', 'id',
  'is', 'it', 'ja', 'ka', 'kk', 'km', 'kn', 'ko', 'ku', 'lg',
  'lij', 'lt', 'lv', 'mai', 'mk', 'ml', 'mn', 'mr', 'ms', 'my',
  'nb-NO', 'nl', 'nn-NO', 'nso', 'oc', 'or', 'pa-IN', 'pl',
  'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'rw', 'sah', 'si', 'sk',
  'sl', 'son', 'sq', 'sr', 'sv-SE', 'sw', 'ta', 'ta-LK', 'te',
  'th', 'tl', 'tn', 'tr', 'uk', 'ur', 'vi', 'wo', 'xh', 'zh-CN',
  'zh-TW', 'zu'
];

function normalizeText(s) {
  return s.replace(/\r\n?/g, '\n').replace(/\uFEFF/g, '');
}

function downloadLanguageFiles(langCode, callback) {
  console.log('Downloading ' + langCode + '...');

  // Constants for constructing the URLs. Translations are taken from the
  // Aurora channel as those are the most recent ones. The Nightly channel
  // does not provide all translations.
  var MOZCENTRAL_ROOT = 'http://mxr.mozilla.org/l10n-mozilla-aurora/source/';
  var MOZCENTRAL_PDFJS_DIR = '/browser/pdfviewer/';
  var MOZCENTRAL_RAW_FLAG = '?raw=1';

  // Defines which files to download for each language.
  var files = ['chrome.properties', 'viewer.properties'];
  var downloadsLeft = files.length;

  if (!fs.existsSync(langCode)) {
    fs.mkdirSync(langCode);
  }

  // Download the necessary files for this language.
  files.forEach(function(fileName) {
    var outputPath = path.join(langCode, fileName);
    var url = MOZCENTRAL_ROOT + langCode + MOZCENTRAL_PDFJS_DIR +
              fileName + MOZCENTRAL_RAW_FLAG;
    var request = http.get(url, function(response) {
      var content = '';
      response.setEncoding('utf8');
      response.on("data", function(chunk) {
        content += chunk;
      });
      response.on('end', function() {
        fs.writeFileSync(outputPath, normalizeText(content), 'utf8');
        downloadsLeft--;
        if (downloadsLeft === 0) {
          callback();
        }
      })
    });
  });
}

function downloadL10n() {
  var i = 0;
  (function next() {
    if (i >= langCodes.length) {
      return;
    }
    downloadLanguageFiles(langCodes[i++], next);
  })();
}

exports.downloadL10n = downloadL10n;
