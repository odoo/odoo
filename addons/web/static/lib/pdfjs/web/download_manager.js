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
/* globals URL, PDFJS */

'use strict';

var DownloadManager = (function DownloadManagerClosure() {

  function download(blobUrl, filename) {
    var a = document.createElement('a');
    if (a.click) {
      // Use a.click() if available. Otherwise, Chrome might show
      // "Unsafe JavaScript attempt to initiate a navigation change
      //  for frame with URL" and not open the PDF at all.
      // Supported by (not mentioned = untested):
      // - Firefox 6 - 19 (4- does not support a.click, 5 ignores a.click)
      // - Chrome 19 - 26 (18- does not support a.click)
      // - Opera 9 - 12.15
      // - Internet Explorer 6 - 10
      // - Safari 6 (5.1- does not support a.click)
      a.href = blobUrl;
      a.target = '_parent';
      // Use a.download if available. This increases the likelihood that
      // the file is downloaded instead of opened by another PDF plugin.
      if ('download' in a) {
        a.download = filename;
      }
      // <a> must be in the document for IE and recent Firefox versions.
      // (otherwise .click() is ignored)
      (document.body || document.documentElement).appendChild(a);
      a.click();
      a.parentNode.removeChild(a);
    } else {
      if (window.top === window &&
          blobUrl.split('#')[0] === window.location.href.split('#')[0]) {
        // If _parent == self, then opening an identical URL with different
        // location hash will only cause a navigation, not a download.
        var padCharacter = blobUrl.indexOf('?') === -1 ? '?' : '&';
        blobUrl = blobUrl.replace(/#|$/, padCharacter + '$&');
      }
      window.open(blobUrl, '_parent');
    }
  }

  function DownloadManager() {}

  DownloadManager.prototype = {
    downloadUrl: function DownloadManager_downloadUrl(url, filename) {
      if (!PDFJS.isValidUrl(url, true)) {
        return; // restricted/invalid URL
      }

      download(url + '#pdfjs.action=download', filename);
    },

    downloadData: function DownloadManager_downloadData(data, filename,
                                                        contentType) {
      if (navigator.msSaveBlob) { // IE10 and above
        return navigator.msSaveBlob(new Blob([data], { type: contentType }),
                                    filename);
      }

      var blobUrl = PDFJS.createObjectURL(data, contentType);
      download(blobUrl, filename);
    },

    download: function DownloadManager_download(blob, url, filename) {
      if (!URL) {
        // URL.createObjectURL is not supported
        this.downloadUrl(url, filename);
        return;
      }

      if (navigator.msSaveBlob) {
        // IE10 / IE11
        if (!navigator.msSaveBlob(blob, filename)) {
          this.downloadUrl(url, filename);
        }
        return;
      }

      var blobUrl = URL.createObjectURL(blob);
      download(blobUrl, filename);
    }
  };

  return DownloadManager;
})();
