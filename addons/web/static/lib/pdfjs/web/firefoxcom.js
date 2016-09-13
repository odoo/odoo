/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
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
/* globals Preferences, PDFJS, Promise */

'use strict';

var FirefoxCom = (function FirefoxComClosure() {
  return {
    /**
     * Creates an event that the extension is listening for and will
     * synchronously respond to.
     * NOTE: It is reccomended to use request() instead since one day we may not
     * be able to synchronously reply.
     * @param {String} action The action to trigger.
     * @param {String} data Optional data to send.
     * @return {*} The response.
     */
    requestSync: function(action, data) {
      var request = document.createTextNode('');
      document.documentElement.appendChild(request);

      var sender = document.createEvent('CustomEvent');
      sender.initCustomEvent('pdf.js.message', true, false,
                             {action: action, data: data, sync: true});
      request.dispatchEvent(sender);
      var response = sender.detail.response;
      document.documentElement.removeChild(request);
      return response;
    },
    /**
     * Creates an event that the extension is listening for and will
     * asynchronously respond by calling the callback.
     * @param {String} action The action to trigger.
     * @param {String} data Optional data to send.
     * @param {Function} callback Optional response callback that will be called
     * with one data argument.
     */
    request: function(action, data, callback) {
      var request = document.createTextNode('');
      if (callback) {
        document.addEventListener('pdf.js.response', function listener(event) {
          var node = event.target;
          var response = event.detail.response;

          document.documentElement.removeChild(node);

          document.removeEventListener('pdf.js.response', listener, false);
          return callback(response);
        }, false);
      }
      document.documentElement.appendChild(request);

      var sender = document.createEvent('CustomEvent');
      sender.initCustomEvent('pdf.js.message', true, false, {
        action: action,
        data: data,
        sync: false,
        responseExpected: !!callback
      });
      return request.dispatchEvent(sender);
    }
  };
})();

var DownloadManager = (function DownloadManagerClosure() {
  function DownloadManager() {}

  DownloadManager.prototype = {
    downloadUrl: function DownloadManager_downloadUrl(url, filename) {
      FirefoxCom.request('download', {
        originalUrl: url,
        filename: filename
      });
    },

    downloadData: function DownloadManager_downloadData(data, filename,
                                                        contentType) {
      var blobUrl = PDFJS.createObjectURL(data, contentType);

      FirefoxCom.request('download', {
        blobUrl: blobUrl,
        originalUrl: blobUrl,
        filename: filename,
        isAttachment: true
      });
    },

    download: function DownloadManager_download(blob, url, filename) {
      var blobUrl = window.URL.createObjectURL(blob);

      FirefoxCom.request('download', {
        blobUrl: blobUrl,
        originalUrl: url,
        filename: filename
      },
        function response(err) {
          if (err && this.onerror) {
            this.onerror(err);
          }
          window.URL.revokeObjectURL(blobUrl);
        }.bind(this)
      );
    }
  };

  return DownloadManager;
})();

Preferences._writeToStorage = function (prefObj) {
  return new Promise(function (resolve) {
    FirefoxCom.request('setPreferences', prefObj, resolve);
  });
};

Preferences._readFromStorage = function (prefObj) {
  return new Promise(function (resolve) {
    FirefoxCom.request('getPreferences', prefObj, function (prefStr) {
      var readPrefs = JSON.parse(prefStr);
      resolve(readPrefs);
    });
  });
};
