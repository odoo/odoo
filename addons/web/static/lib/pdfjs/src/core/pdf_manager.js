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
/* globals NotImplementedException, MissingDataException, Promise, Stream,
           PDFDocument, ChunkedStreamManager, createPromiseCapability */

'use strict';

// The maximum number of bytes fetched per range request
var RANGE_CHUNK_SIZE = 65536;

// TODO(mack): Make use of PDFJS.Util.inherit() when it becomes available
var BasePdfManager = (function BasePdfManagerClosure() {
  function BasePdfManager() {
    throw new Error('Cannot initialize BaseManagerManager');
  }

  BasePdfManager.prototype = {
    onLoadedStream: function BasePdfManager_onLoadedStream() {
      throw new NotImplementedException();
    },

    ensureDoc: function BasePdfManager_ensureDoc(prop, args) {
      return this.ensure(this.pdfDocument, prop, args);
    },

    ensureXRef: function BasePdfManager_ensureXRef(prop, args) {
      return this.ensure(this.pdfDocument.xref, prop, args);
    },

    ensureCatalog: function BasePdfManager_ensureCatalog(prop, args) {
      return this.ensure(this.pdfDocument.catalog, prop, args);
    },

    getPage: function BasePdfManager_pagePage(pageIndex) {
      return this.pdfDocument.getPage(pageIndex);
    },

    cleanup: function BasePdfManager_cleanup() {
      return this.pdfDocument.cleanup();
    },

    ensure: function BasePdfManager_ensure(obj, prop, args) {
      return new NotImplementedException();
    },

    requestRange: function BasePdfManager_ensure(begin, end) {
      return new NotImplementedException();
    },

    requestLoadedStream: function BasePdfManager_requestLoadedStream() {
      return new NotImplementedException();
    },

    sendProgressiveData: function BasePdfManager_sendProgressiveData(chunk) {
      return new NotImplementedException();
    },

    updatePassword: function BasePdfManager_updatePassword(password) {
      this.pdfDocument.xref.password = this.password = password;
      if (this._passwordChangedCapability) {
        this._passwordChangedCapability.resolve();
      }
    },

    passwordChanged: function BasePdfManager_passwordChanged() {
      this._passwordChangedCapability = createPromiseCapability();
      return this._passwordChangedCapability.promise;
    },

    terminate: function BasePdfManager_terminate() {
      return new NotImplementedException();
    }
  };

  return BasePdfManager;
})();

var LocalPdfManager = (function LocalPdfManagerClosure() {
  function LocalPdfManager(data, password) {
    var stream = new Stream(data);
    this.pdfDocument = new PDFDocument(this, stream, password);
    this._loadedStreamCapability = createPromiseCapability();
    this._loadedStreamCapability.resolve(stream);
  }

  LocalPdfManager.prototype = Object.create(BasePdfManager.prototype);
  LocalPdfManager.prototype.constructor = LocalPdfManager;

  LocalPdfManager.prototype.ensure =
      function LocalPdfManager_ensure(obj, prop, args) {
    return new Promise(function (resolve, reject) {
      try {
        var value = obj[prop];
        var result;
        if (typeof value === 'function') {
          result = value.apply(obj, args);
        } else {
          result = value;
        }
        resolve(result);
      } catch (e) {
        reject(e);
      }
    });
  };

  LocalPdfManager.prototype.requestRange =
      function LocalPdfManager_requestRange(begin, end) {
    return Promise.resolve();
  };

  LocalPdfManager.prototype.requestLoadedStream =
      function LocalPdfManager_requestLoadedStream() {
  };

  LocalPdfManager.prototype.onLoadedStream =
      function LocalPdfManager_getLoadedStream() {
    return this._loadedStreamCapability.promise;
  };

  LocalPdfManager.prototype.terminate =
      function LocalPdfManager_terminate() {
    return;
  };

  return LocalPdfManager;
})();

var NetworkPdfManager = (function NetworkPdfManagerClosure() {
  function NetworkPdfManager(args, msgHandler) {

    this.msgHandler = msgHandler;

    var params = {
      msgHandler: msgHandler,
      httpHeaders: args.httpHeaders,
      withCredentials: args.withCredentials,
      chunkedViewerLoading: args.chunkedViewerLoading,
      disableAutoFetch: args.disableAutoFetch,
      initialData: args.initialData
    };
    this.streamManager = new ChunkedStreamManager(args.length, RANGE_CHUNK_SIZE,
                                                  args.url, params);

    this.pdfDocument = new PDFDocument(this, this.streamManager.getStream(),
                                    args.password);
  }

  NetworkPdfManager.prototype = Object.create(BasePdfManager.prototype);
  NetworkPdfManager.prototype.constructor = NetworkPdfManager;

  NetworkPdfManager.prototype.ensure =
      function NetworkPdfManager_ensure(obj, prop, args) {
    var pdfManager = this;

    return new Promise(function (resolve, reject) {
      function ensureHelper() {
        try {
          var result;
          var value = obj[prop];
          if (typeof value === 'function') {
            result = value.apply(obj, args);
          } else {
            result = value;
          }
          resolve(result);
        } catch(e) {
          if (!(e instanceof MissingDataException)) {
            reject(e);
            return;
          }
          pdfManager.streamManager.requestRange(e.begin, e.end, ensureHelper);
        }
      }

      ensureHelper();
    });
  };

  NetworkPdfManager.prototype.requestRange =
      function NetworkPdfManager_requestRange(begin, end) {
    return new Promise(function (resolve) {
      this.streamManager.requestRange(begin, end, function() {
        resolve();
      });
    }.bind(this));
  };

  NetworkPdfManager.prototype.requestLoadedStream =
      function NetworkPdfManager_requestLoadedStream() {
    this.streamManager.requestAllChunks();
  };

  NetworkPdfManager.prototype.sendProgressiveData =
      function NetworkPdfManager_sendProgressiveData(chunk) {
    this.streamManager.onReceiveData({ chunk: chunk });
  };

  NetworkPdfManager.prototype.onLoadedStream =
      function NetworkPdfManager_getLoadedStream() {
    return this.streamManager.onLoadedStream();
  };

  NetworkPdfManager.prototype.terminate =
      function NetworkPdfManager_terminate() {
    this.streamManager.networkManager.abortAllRequests();
  };

  return NetworkPdfManager;
})();
