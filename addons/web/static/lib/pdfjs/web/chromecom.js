/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* Copyright 2013 Mozilla Foundation
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

/* globals chrome, PDFJS, PDFViewerApplication */
'use strict';

var ChromeCom = (function ChromeComClosure() {
  var ChromeCom = {};
  /**
   * Creates an event that the extension is listening for and will
   * asynchronously respond by calling the callback.
   *
   * @param {String} action The action to trigger.
   * @param {String} data Optional data to send.
   * @param {Function} callback Optional response callback that will be called
   * with one data argument. When the request cannot be handled, the callback
   * is immediately invoked with no arguments.
   */
  ChromeCom.request = function ChromeCom_request(action, data, callback) {
    var message = {
      action: action,
      data: data
    };
    if (!chrome.runtime) {
      console.error('chrome.runtime is undefined.');
      if (callback) {
        callback();
      }
    } else if (callback) {
      chrome.runtime.sendMessage(message, callback);
    } else {
      chrome.runtime.sendMessage(message);
    }
  };

  /**
   * Opens a PDF file with the PDF viewer.
   *
   * @param {String} file Absolute URL of PDF file.
   */
  ChromeCom.openPDFFile = function ChromeCom_openPDFFile(file) {
    // Expand drive:-URLs to filesystem URLs (Chrome OS)
    file = file.replace(/^drive:/i,
        'filesystem:' + location.origin + '/external/');

    ChromeCom.request('getPDFStream', file, function(response) {
      if (response) {
        // We will only get a response when the streamsPrivate API is available.

        var isFTPFile = /^ftp:/i.test(file);
        var streamUrl = response.streamUrl;
        if (streamUrl) {
          console.log('Found data stream for ' + file);
          PDFViewerApplication.open(streamUrl, 0, undefined, undefined, {
            length: response.contentLength
          });
          PDFViewerApplication.setTitleUsingUrl(file);
          return;
        }
        if (isFTPFile && !response.extensionSupportsFTP) {
          // Stream not found, and it's loaded from FTP.
          // When the browser does not support loading ftp resources over
          // XMLHttpRequest, just reload the page.
          // NOTE: This will not lead to an infinite redirect loop, because
          // if the file exists, then the streamsPrivate API will capture the
          // stream and send back the response. If the stream does not exist,
          // a "Webpage not available" error will be shown (not the PDF Viewer).
          location.replace(file);
          return;
        }
      }
      if (/^filesystem:/.test(file) && !PDFJS.disableWorker) {
        // The security origin of filesystem:-URLs are not preserved when the
        // URL is passed to a Web worker, (http://crbug.com/362061), so we have
        // to create an intermediate blob:-URL as a work-around.
        var resolveLocalFileSystemURL = window.resolveLocalFileSystemURL ||
                                        window.webkitResolveLocalFileSystemURL;
        resolveLocalFileSystemURL(file, function onResolvedFSURL(fileEntry) {
          fileEntry.file(function(fileObject) {
            var blobUrl = URL.createObjectURL(fileObject);
            PDFViewerApplication.open(blobUrl, 0, undefined, undefined, {
              length: fileObject.size
            });
          });
        }, function onFileSystemError(error) {
          // This should not happen. When it happens, just fall back to the
          // usual way of getting the File's data (via the Web worker).
          console.warn('Cannot resolve file ' + file + ', ' + error.name + ' ' +
                       error.message);
          PDFViewerApplication.open(file, 0);
        });
        return;
      }
      PDFViewerApplication.open(file, 0);
    });
  };
  return ChromeCom;
})();
