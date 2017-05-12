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
/* globals PDFJS, createPromiseCapability, LocalPdfManager, NetworkPdfManager,
           NetworkManager, isInt, RANGE_CHUNK_SIZE, MissingPDFException,
           UnexpectedResponseException, PasswordException, Promise, warn,
           PasswordResponses, InvalidPDFException, UnknownErrorException,
           XRefParseException, Ref, info, globalScope, error, MessageHandler */

'use strict';

var WorkerMessageHandler = PDFJS.WorkerMessageHandler = {
  setup: function wphSetup(handler) {
    var pdfManager;

    function loadDocument(recoveryMode) {
      var loadDocumentCapability = createPromiseCapability();

      var parseSuccess = function parseSuccess() {
        var numPagesPromise = pdfManager.ensureDoc('numPages');
        var fingerprintPromise = pdfManager.ensureDoc('fingerprint');
        var encryptedPromise = pdfManager.ensureXRef('encrypt');
        Promise.all([numPagesPromise, fingerprintPromise,
                     encryptedPromise]).then(function onDocReady(results) {
          var doc = {
            numPages: results[0],
            fingerprint: results[1],
            encrypted: !!results[2],
          };
          loadDocumentCapability.resolve(doc);
        },
        parseFailure);
      };

      var parseFailure = function parseFailure(e) {
        loadDocumentCapability.reject(e);
      };

      pdfManager.ensureDoc('checkHeader', []).then(function() {
        pdfManager.ensureDoc('parseStartXRef', []).then(function() {
          pdfManager.ensureDoc('parse', [recoveryMode]).then(
            parseSuccess, parseFailure);
        }, parseFailure);
      }, parseFailure);

      return loadDocumentCapability.promise;
    }

    function getPdfManager(data) {
      var pdfManagerCapability = createPromiseCapability();

      var source = data.source;
      var disableRange = data.disableRange;
      if (source.data) {
        try {
          pdfManager = new LocalPdfManager(source.data, source.password);
          pdfManagerCapability.resolve();
        } catch (ex) {
          pdfManagerCapability.reject(ex);
        }
        return pdfManagerCapability.promise;
      } else if (source.chunkedViewerLoading) {
        try {
          pdfManager = new NetworkPdfManager(source, handler);
          pdfManagerCapability.resolve();
        } catch (ex) {
          pdfManagerCapability.reject(ex);
        }
        return pdfManagerCapability.promise;
      }

      var networkManager = new NetworkManager(source.url, {
        httpHeaders: source.httpHeaders,
        withCredentials: source.withCredentials
      });
      var cachedChunks = [];
      var fullRequestXhrId = networkManager.requestFull({
        onHeadersReceived: function onHeadersReceived() {
          if (disableRange) {
            return;
          }

          var fullRequestXhr = networkManager.getRequestXhr(fullRequestXhrId);
          if (fullRequestXhr.getResponseHeader('Accept-Ranges') !== 'bytes') {
            return;
          }

          var contentEncoding =
            fullRequestXhr.getResponseHeader('Content-Encoding') || 'identity';
          if (contentEncoding !== 'identity') {
            return;
          }

          var length = fullRequestXhr.getResponseHeader('Content-Length');
          length = parseInt(length, 10);
          if (!isInt(length)) {
            return;
          }
          source.length = length;
          if (length <= 2 * RANGE_CHUNK_SIZE) {
            // The file size is smaller than the size of two chunks, so it does
            // not make any sense to abort the request and retry with a range
            // request.
            return;
          }

          if (networkManager.isStreamingRequest(fullRequestXhrId)) {
            // We can continue fetching when progressive loading is enabled,
            // and we don't need the autoFetch feature.
            source.disableAutoFetch = true;
          } else {
            // NOTE: by cancelling the full request, and then issuing range
            // requests, there will be an issue for sites where you can only
            // request the pdf once. However, if this is the case, then the
            // server should not be returning that it can support range
            // requests.
            networkManager.abortRequest(fullRequestXhrId);
          }

          try {
            pdfManager = new NetworkPdfManager(source, handler);
            pdfManagerCapability.resolve(pdfManager);
          } catch (ex) {
            pdfManagerCapability.reject(ex);
          }
        },

        onProgressiveData: source.disableStream ? null :
            function onProgressiveData(chunk) {
          if (!pdfManager) {
            cachedChunks.push(chunk);
            return;
          }
          pdfManager.sendProgressiveData(chunk);
        },

        onDone: function onDone(args) {
          if (pdfManager) {
            return; // already processed
          }

          var pdfFile;
          if (args === null) {
            // TODO add some streaming manager, e.g. for unknown length files.
            // The data was returned in the onProgressiveData, combining...
            var pdfFileLength = 0, pos = 0;
            cachedChunks.forEach(function (chunk) {
              pdfFileLength += chunk.byteLength;
            });
            if (source.length && pdfFileLength !== source.length) {
              warn('reported HTTP length is different from actual');
            }
            var pdfFileArray = new Uint8Array(pdfFileLength);
            cachedChunks.forEach(function (chunk) {
              pdfFileArray.set(new Uint8Array(chunk), pos);
              pos += chunk.byteLength;
            });
            pdfFile = pdfFileArray.buffer;
          } else {
            pdfFile = args.chunk;
          }

          // the data is array, instantiating directly from it
          try {
            pdfManager = new LocalPdfManager(pdfFile, source.password);
            pdfManagerCapability.resolve();
          } catch (ex) {
            pdfManagerCapability.reject(ex);
          }
        },

        onError: function onError(status) {
          var exception;
          if (status === 404) {
            exception = new MissingPDFException('Missing PDF "' +
                                                source.url + '".');
            handler.send('MissingPDF', exception);
          } else {
            exception = new UnexpectedResponseException(
              'Unexpected server response (' + status +
              ') while retrieving PDF "' + source.url + '".', status);
            handler.send('UnexpectedResponse', exception);
          }
        },

        onProgress: function onProgress(evt) {
          handler.send('DocProgress', {
            loaded: evt.loaded,
            total: evt.lengthComputable ? evt.total : source.length
          });
        }
      });

      return pdfManagerCapability.promise;
    }

    handler.on('test', function wphSetupTest(data) {
      // check if Uint8Array can be sent to worker
      if (!(data instanceof Uint8Array)) {
        handler.send('test', false);
        return;
      }
      // making sure postMessage transfers are working
      var supportTransfers = data[0] === 255;
      handler.postMessageTransfers = supportTransfers;
      // check if the response property is supported by xhr
      var xhr = new XMLHttpRequest();
      var responseExists = 'response' in xhr;
      // check if the property is actually implemented
      try {
        var dummy = xhr.responseType;
      } catch (e) {
        responseExists = false;
      }
      if (!responseExists) {
        handler.send('test', false);
        return;
      }
      handler.send('test', {
        supportTypedArray: true,
        supportTransfers: supportTransfers
      });
    });

    handler.on('GetDocRequest', function wphSetupDoc(data) {

      var onSuccess = function(doc) {
        handler.send('GetDoc', { pdfInfo: doc });
      };

      var onFailure = function(e) {
        if (e instanceof PasswordException) {
          if (e.code === PasswordResponses.NEED_PASSWORD) {
            handler.send('NeedPassword', e);
          } else if (e.code === PasswordResponses.INCORRECT_PASSWORD) {
            handler.send('IncorrectPassword', e);
          }
        } else if (e instanceof InvalidPDFException) {
          handler.send('InvalidPDF', e);
        } else if (e instanceof MissingPDFException) {
          handler.send('MissingPDF', e);
        } else if (e instanceof UnexpectedResponseException) {
          handler.send('UnexpectedResponse', e);
        } else {
          handler.send('UnknownError',
                       new UnknownErrorException(e.message, e.toString()));
        }
      };

      PDFJS.maxImageSize = data.maxImageSize === undefined ?
                           -1 : data.maxImageSize;
      PDFJS.disableFontFace = data.disableFontFace;
      PDFJS.disableCreateObjectURL = data.disableCreateObjectURL;
      PDFJS.verbosity = data.verbosity;
      PDFJS.cMapUrl = data.cMapUrl === undefined ?
                           null : data.cMapUrl;
      PDFJS.cMapPacked = data.cMapPacked === true;

      getPdfManager(data).then(function () {
        handler.send('PDFManagerReady', null);
        pdfManager.onLoadedStream().then(function(stream) {
          handler.send('DataLoaded', { length: stream.bytes.byteLength });
        });
      }).then(function pdfManagerReady() {
        loadDocument(false).then(onSuccess, function loadFailure(ex) {
          // Try again with recoveryMode == true
          if (!(ex instanceof XRefParseException)) {
            if (ex instanceof PasswordException) {
              // after password exception prepare to receive a new password
              // to repeat loading
              pdfManager.passwordChanged().then(pdfManagerReady);
            }

            onFailure(ex);
            return;
          }

          pdfManager.requestLoadedStream();
          pdfManager.onLoadedStream().then(function() {
            loadDocument(true).then(onSuccess, onFailure);
          });
        }, onFailure);
      }, onFailure);
    });

    handler.on('GetPage', function wphSetupGetPage(data) {
      return pdfManager.getPage(data.pageIndex).then(function(page) {
        var rotatePromise = pdfManager.ensure(page, 'rotate');
        var refPromise = pdfManager.ensure(page, 'ref');
        var viewPromise = pdfManager.ensure(page, 'view');

        return Promise.all([rotatePromise, refPromise, viewPromise]).then(
            function(results) {
          return {
            rotate: results[0],
            ref: results[1],
            view: results[2]
          };
        });
      });
    });

    handler.on('GetPageIndex', function wphSetupGetPageIndex(data) {
      var ref = new Ref(data.ref.num, data.ref.gen);
      var catalog = pdfManager.pdfDocument.catalog;
      return catalog.getPageIndex(ref);
    });

    handler.on('GetDestinations',
      function wphSetupGetDestinations(data) {
        return pdfManager.ensureCatalog('destinations');
      }
    );

    handler.on('GetDestination',
      function wphSetupGetDestination(data) {
        return pdfManager.ensureCatalog('getDestination', [ data.id ]);
      }
    );

    handler.on('GetAttachments',
      function wphSetupGetAttachments(data) {
        return pdfManager.ensureCatalog('attachments');
      }
    );

    handler.on('GetJavaScript',
      function wphSetupGetJavaScript(data) {
        return pdfManager.ensureCatalog('javaScript');
      }
    );

    handler.on('GetOutline',
      function wphSetupGetOutline(data) {
        return pdfManager.ensureCatalog('documentOutline');
      }
    );

    handler.on('GetMetadata',
      function wphSetupGetMetadata(data) {
        return Promise.all([pdfManager.ensureDoc('documentInfo'),
                            pdfManager.ensureCatalog('metadata')]);
      }
    );

    handler.on('GetData', function wphSetupGetData(data) {
      pdfManager.requestLoadedStream();
      return pdfManager.onLoadedStream().then(function(stream) {
        return stream.bytes;
      });
    });

    handler.on('GetStats',
      function wphSetupGetStats(data) {
        return pdfManager.pdfDocument.xref.stats;
      }
    );

    handler.on('UpdatePassword', function wphSetupUpdatePassword(data) {
      pdfManager.updatePassword(data);
    });

    handler.on('GetAnnotations', function wphSetupGetAnnotations(data) {
      return pdfManager.getPage(data.pageIndex).then(function(page) {
        return pdfManager.ensure(page, 'getAnnotationsData', []);
      });
    });

    handler.on('RenderPageRequest', function wphSetupRenderPage(data) {
      pdfManager.getPage(data.pageIndex).then(function(page) {

        var pageNum = data.pageIndex + 1;
        var start = Date.now();
        // Pre compile the pdf page and fetch the fonts/images.
        page.getOperatorList(handler, data.intent).then(function(operatorList) {

          info('page=' + pageNum + ' - getOperatorList: time=' +
               (Date.now() - start) + 'ms, len=' + operatorList.fnArray.length);

        }, function(e) {

          var minimumStackMessage =
            'worker.js: while trying to getPage() and getOperatorList()';

          var wrappedException;

          // Turn the error into an obj that can be serialized
          if (typeof e === 'string') {
            wrappedException = {
              message: e,
              stack: minimumStackMessage
            };
          } else if (typeof e === 'object') {
            wrappedException = {
              message: e.message || e.toString(),
              stack: e.stack || minimumStackMessage
            };
          } else {
            wrappedException = {
              message: 'Unknown exception type: ' + (typeof e),
              stack: minimumStackMessage
            };
          }

          handler.send('PageError', {
            pageNum: pageNum,
            error: wrappedException,
            intent: data.intent
          });
        });
      });
    }, this);

    handler.on('GetTextContent', function wphExtractText(data) {
      return pdfManager.getPage(data.pageIndex).then(function(page) {
        var pageNum = data.pageIndex + 1;
        var start = Date.now();
        return page.extractTextContent().then(function(textContent) {
          info('text indexing: page=' + pageNum + ' - time=' +
               (Date.now() - start) + 'ms');
          return textContent;
        });
      });
    });

    handler.on('Cleanup', function wphCleanup(data) {
      return pdfManager.cleanup();
    });

    handler.on('Terminate', function wphTerminate(data) {
      pdfManager.terminate();
    });
  }
};

var consoleTimer = {};

var workerConsole = {
  log: function log() {
    var args = Array.prototype.slice.call(arguments);
    globalScope.postMessage({
      action: 'console_log',
      data: args
    });
  },

  error: function error() {
    var args = Array.prototype.slice.call(arguments);
    globalScope.postMessage({
      action: 'console_error',
      data: args
    });
    throw 'pdf.js execution error';
  },

  time: function time(name) {
    consoleTimer[name] = Date.now();
  },

  timeEnd: function timeEnd(name) {
    var time = consoleTimer[name];
    if (!time) {
      error('Unknown timer name ' + name);
    }
    this.log('Timer:', name, Date.now() - time);
  }
};


// Worker thread?
if (typeof window === 'undefined') {
  if (!('console' in globalScope)) {
    globalScope.console = workerConsole;
  }

  // Listen for unsupported features so we can pass them on to the main thread.
  PDFJS.UnsupportedManager.listen(function (msg) {
    globalScope.postMessage({
      action: '_unsupported_feature',
      data: msg
    });
  });

  var handler = new MessageHandler('worker_processor', this);
  WorkerMessageHandler.setup(handler);
}
