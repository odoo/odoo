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
/* globals assert, MissingDataException, isInt, NetworkManager, Promise,
           isEmptyObj, createPromiseCapability */

'use strict';

var ChunkedStream = (function ChunkedStreamClosure() {
  function ChunkedStream(length, chunkSize, manager) {
    this.bytes = new Uint8Array(length);
    this.start = 0;
    this.pos = 0;
    this.end = length;
    this.chunkSize = chunkSize;
    this.loadedChunks = [];
    this.numChunksLoaded = 0;
    this.numChunks = Math.ceil(length / chunkSize);
    this.manager = manager;
    this.progressiveDataLength = 0;
    this.lastSuccessfulEnsureByteChunk = -1;  // a single-entry cache
  }

  // required methods for a stream. if a particular stream does not
  // implement these, an error should be thrown
  ChunkedStream.prototype = {

    getMissingChunks: function ChunkedStream_getMissingChunks() {
      var chunks = [];
      for (var chunk = 0, n = this.numChunks; chunk < n; ++chunk) {
        if (!this.loadedChunks[chunk]) {
          chunks.push(chunk);
        }
      }
      return chunks;
    },

    getBaseStreams: function ChunkedStream_getBaseStreams() {
      return [this];
    },

    allChunksLoaded: function ChunkedStream_allChunksLoaded() {
      return this.numChunksLoaded === this.numChunks;
    },

    onReceiveData: function ChunkedStream_onReceiveData(begin, chunk) {
      var end = begin + chunk.byteLength;

      assert(begin % this.chunkSize === 0, 'Bad begin offset: ' + begin);
      // Using this.length is inaccurate here since this.start can be moved
      // See ChunkedStream.moveStart()
      var length = this.bytes.length;
      assert(end % this.chunkSize === 0 || end === length,
             'Bad end offset: ' + end);

      this.bytes.set(new Uint8Array(chunk), begin);
      var chunkSize = this.chunkSize;
      var beginChunk = Math.floor(begin / chunkSize);
      var endChunk = Math.floor((end - 1) / chunkSize) + 1;
      var curChunk;

      for (curChunk = beginChunk; curChunk < endChunk; ++curChunk) {
        if (!this.loadedChunks[curChunk]) {
          this.loadedChunks[curChunk] = true;
          ++this.numChunksLoaded;
        }
      }
    },

    onReceiveProgressiveData:
        function ChunkedStream_onReceiveProgressiveData(data) {
      var position = this.progressiveDataLength;
      var beginChunk = Math.floor(position / this.chunkSize);

      this.bytes.set(new Uint8Array(data), position);
      position += data.byteLength;
      this.progressiveDataLength = position;
      var endChunk = position >= this.end ? this.numChunks :
                     Math.floor(position / this.chunkSize);
      var curChunk;
      for (curChunk = beginChunk; curChunk < endChunk; ++curChunk) {
        if (!this.loadedChunks[curChunk]) {
          this.loadedChunks[curChunk] = true;
          ++this.numChunksLoaded;
        }
      }
    },

    ensureByte: function ChunkedStream_ensureByte(pos) {
      var chunk = Math.floor(pos / this.chunkSize);
      if (chunk === this.lastSuccessfulEnsureByteChunk) {
        return;
      }

      if (!this.loadedChunks[chunk]) {
        throw new MissingDataException(pos, pos + 1);
      }
      this.lastSuccessfulEnsureByteChunk = chunk;
    },

    ensureRange: function ChunkedStream_ensureRange(begin, end) {
      if (begin >= end) {
        return;
      }

      if (end <= this.progressiveDataLength) {
        return;
      }

      var chunkSize = this.chunkSize;
      var beginChunk = Math.floor(begin / chunkSize);
      var endChunk = Math.floor((end - 1) / chunkSize) + 1;
      for (var chunk = beginChunk; chunk < endChunk; ++chunk) {
        if (!this.loadedChunks[chunk]) {
          throw new MissingDataException(begin, end);
        }
      }
    },

    nextEmptyChunk: function ChunkedStream_nextEmptyChunk(beginChunk) {
      var chunk, n;
      for (chunk = beginChunk, n = this.numChunks; chunk < n; ++chunk) {
        if (!this.loadedChunks[chunk]) {
          return chunk;
        }
      }
      // Wrap around to beginning
      for (chunk = 0; chunk < beginChunk; ++chunk) {
        if (!this.loadedChunks[chunk]) {
          return chunk;
        }
      }
      return null;
    },

    hasChunk: function ChunkedStream_hasChunk(chunk) {
      return !!this.loadedChunks[chunk];
    },

    get length() {
      return this.end - this.start;
    },

    get isEmpty() {
      return this.length === 0;
    },

    getByte: function ChunkedStream_getByte() {
      var pos = this.pos;
      if (pos >= this.end) {
        return -1;
      }
      this.ensureByte(pos);
      return this.bytes[this.pos++];
    },

    getUint16: function ChunkedStream_getUint16() {
      var b0 = this.getByte();
      var b1 = this.getByte();
      if (b0 === -1 || b1 === -1) {
        return -1;
      }
      return (b0 << 8) + b1;
    },

    getInt32: function ChunkedStream_getInt32() {
      var b0 = this.getByte();
      var b1 = this.getByte();
      var b2 = this.getByte();
      var b3 = this.getByte();
      return (b0 << 24) + (b1 << 16) + (b2 << 8) + b3;
    },

    // returns subarray of original buffer
    // should only be read
    getBytes: function ChunkedStream_getBytes(length) {
      var bytes = this.bytes;
      var pos = this.pos;
      var strEnd = this.end;

      if (!length) {
        this.ensureRange(pos, strEnd);
        return bytes.subarray(pos, strEnd);
      }

      var end = pos + length;
      if (end > strEnd) {
        end = strEnd;
      }
      this.ensureRange(pos, end);

      this.pos = end;
      return bytes.subarray(pos, end);
    },

    peekByte: function ChunkedStream_peekByte() {
      var peekedByte = this.getByte();
      this.pos--;
      return peekedByte;
    },

    peekBytes: function ChunkedStream_peekBytes(length) {
      var bytes = this.getBytes(length);
      this.pos -= bytes.length;
      return bytes;
    },

    getByteRange: function ChunkedStream_getBytes(begin, end) {
      this.ensureRange(begin, end);
      return this.bytes.subarray(begin, end);
    },

    skip: function ChunkedStream_skip(n) {
      if (!n) {
        n = 1;
      }
      this.pos += n;
    },

    reset: function ChunkedStream_reset() {
      this.pos = this.start;
    },

    moveStart: function ChunkedStream_moveStart() {
      this.start = this.pos;
    },

    makeSubStream: function ChunkedStream_makeSubStream(start, length, dict) {
      this.ensureRange(start, start + length);

      function ChunkedStreamSubstream() {}
      ChunkedStreamSubstream.prototype = Object.create(this);
      ChunkedStreamSubstream.prototype.getMissingChunks = function() {
        var chunkSize = this.chunkSize;
        var beginChunk = Math.floor(this.start / chunkSize);
        var endChunk = Math.floor((this.end - 1) / chunkSize) + 1;
        var missingChunks = [];
        for (var chunk = beginChunk; chunk < endChunk; ++chunk) {
          if (!this.loadedChunks[chunk]) {
            missingChunks.push(chunk);
          }
        }
        return missingChunks;
      };
      var subStream = new ChunkedStreamSubstream();
      subStream.pos = subStream.start = start;
      subStream.end = start + length || this.end;
      subStream.dict = dict;
      return subStream;
    },

    isStream: true
  };

  return ChunkedStream;
})();

var ChunkedStreamManager = (function ChunkedStreamManagerClosure() {

  function ChunkedStreamManager(length, chunkSize, url, args) {
    this.stream = new ChunkedStream(length, chunkSize, this);
    this.length = length;
    this.chunkSize = chunkSize;
    this.url = url;
    this.disableAutoFetch = args.disableAutoFetch;
    var msgHandler = this.msgHandler = args.msgHandler;

    if (args.chunkedViewerLoading) {
      msgHandler.on('OnDataRange', this.onReceiveData.bind(this));
      msgHandler.on('OnDataProgress', this.onProgress.bind(this));
      this.sendRequest = function ChunkedStreamManager_sendRequest(begin, end) {
        msgHandler.send('RequestDataRange', { begin: begin, end: end });
      };
    } else {

      var getXhr = function getXhr() {
//#if B2G
//      return new XMLHttpRequest({ mozSystem: true });
//#else
        return new XMLHttpRequest();
//#endif
      };
      this.networkManager = new NetworkManager(this.url, {
        getXhr: getXhr,
        httpHeaders: args.httpHeaders,
        withCredentials: args.withCredentials
      });
      this.sendRequest = function ChunkedStreamManager_sendRequest(begin, end) {
        this.networkManager.requestRange(begin, end, {
          onDone: this.onReceiveData.bind(this),
          onProgress: this.onProgress.bind(this)
        });
      };
    }

    this.currRequestId = 0;

    this.chunksNeededByRequest = {};
    this.requestsByChunk = {};
    this.callbacksByRequest = {};
    this.progressiveDataLength = 0;

    this._loadedStreamCapability = createPromiseCapability();

    if (args.initialData) {
      this.onReceiveData({chunk: args.initialData});
    }
  }

  ChunkedStreamManager.prototype = {
    onLoadedStream: function ChunkedStreamManager_getLoadedStream() {
      return this._loadedStreamCapability.promise;
    },

    // Get all the chunks that are not yet loaded and groups them into
    // contiguous ranges to load in as few requests as possible
    requestAllChunks: function ChunkedStreamManager_requestAllChunks() {
      var missingChunks = this.stream.getMissingChunks();
      this.requestChunks(missingChunks);
      return this._loadedStreamCapability.promise;
    },

    requestChunks: function ChunkedStreamManager_requestChunks(chunks,
                                                               callback) {
      var requestId = this.currRequestId++;

      var chunksNeeded;
      var i, ii;
      this.chunksNeededByRequest[requestId] = chunksNeeded = {};
      for (i = 0, ii = chunks.length; i < ii; i++) {
        if (!this.stream.hasChunk(chunks[i])) {
          chunksNeeded[chunks[i]] = true;
        }
      }

      if (isEmptyObj(chunksNeeded)) {
        if (callback) {
          callback();
        }
        return;
      }

      this.callbacksByRequest[requestId] = callback;

      var chunksToRequest = [];
      for (var chunk in chunksNeeded) {
        chunk = chunk | 0;
        if (!(chunk in this.requestsByChunk)) {
          this.requestsByChunk[chunk] = [];
          chunksToRequest.push(chunk);
        }
        this.requestsByChunk[chunk].push(requestId);
      }

      if (!chunksToRequest.length) {
        return;
      }

      var groupedChunksToRequest = this.groupChunks(chunksToRequest);

      for (i = 0; i < groupedChunksToRequest.length; ++i) {
        var groupedChunk = groupedChunksToRequest[i];
        var begin = groupedChunk.beginChunk * this.chunkSize;
        var end = Math.min(groupedChunk.endChunk * this.chunkSize, this.length);
        this.sendRequest(begin, end);
      }
    },

    getStream: function ChunkedStreamManager_getStream() {
      return this.stream;
    },

    // Loads any chunks in the requested range that are not yet loaded
    requestRange: function ChunkedStreamManager_requestRange(
                      begin, end, callback) {

      end = Math.min(end, this.length);

      var beginChunk = this.getBeginChunk(begin);
      var endChunk = this.getEndChunk(end);

      var chunks = [];
      for (var chunk = beginChunk; chunk < endChunk; ++chunk) {
        chunks.push(chunk);
      }

      this.requestChunks(chunks, callback);
    },

    requestRanges: function ChunkedStreamManager_requestRanges(ranges,
                                                               callback) {
      ranges = ranges || [];
      var chunksToRequest = [];

      for (var i = 0; i < ranges.length; i++) {
        var beginChunk = this.getBeginChunk(ranges[i].begin);
        var endChunk = this.getEndChunk(ranges[i].end);
        for (var chunk = beginChunk; chunk < endChunk; ++chunk) {
          if (chunksToRequest.indexOf(chunk) < 0) {
            chunksToRequest.push(chunk);
          }
        }
      }

      chunksToRequest.sort(function(a, b) { return a - b; });
      this.requestChunks(chunksToRequest, callback);
    },

    // Groups a sorted array of chunks into as few continguous larger
    // chunks as possible
    groupChunks: function ChunkedStreamManager_groupChunks(chunks) {
      var groupedChunks = [];
      var beginChunk = -1;
      var prevChunk = -1;
      for (var i = 0; i < chunks.length; ++i) {
        var chunk = chunks[i];

        if (beginChunk < 0) {
          beginChunk = chunk;
        }

        if (prevChunk >= 0 && prevChunk + 1 !== chunk) {
          groupedChunks.push({ beginChunk: beginChunk,
                               endChunk: prevChunk + 1 });
          beginChunk = chunk;
        }
        if (i + 1 === chunks.length) {
          groupedChunks.push({ beginChunk: beginChunk,
                               endChunk: chunk + 1 });
        }

        prevChunk = chunk;
      }
      return groupedChunks;
    },

    onProgress: function ChunkedStreamManager_onProgress(args) {
      var bytesLoaded = (this.stream.numChunksLoaded * this.chunkSize +
                         args.loaded);
      this.msgHandler.send('DocProgress', {
        loaded: bytesLoaded,
        total: this.length
      });
    },

    onReceiveData: function ChunkedStreamManager_onReceiveData(args) {
      var chunk = args.chunk;
      var isProgressive = args.begin === undefined;
      var begin = isProgressive ? this.progressiveDataLength : args.begin;
      var end = begin + chunk.byteLength;

      var beginChunk = Math.floor(begin / this.chunkSize);
      var endChunk = end < this.length ? Math.floor(end / this.chunkSize) :
                                         Math.ceil(end / this.chunkSize);

      if (isProgressive) {
        this.stream.onReceiveProgressiveData(chunk);
        this.progressiveDataLength = end;
      } else {
        this.stream.onReceiveData(begin, chunk);
      }

      if (this.stream.allChunksLoaded()) {
        this._loadedStreamCapability.resolve(this.stream);
      }

      var loadedRequests = [];
      var i, requestId;
      for (chunk = beginChunk; chunk < endChunk; ++chunk) {
        // The server might return more chunks than requested
        var requestIds = this.requestsByChunk[chunk] || [];
        delete this.requestsByChunk[chunk];

        for (i = 0; i < requestIds.length; ++i) {
          requestId = requestIds[i];
          var chunksNeeded = this.chunksNeededByRequest[requestId];
          if (chunk in chunksNeeded) {
            delete chunksNeeded[chunk];
          }

          if (!isEmptyObj(chunksNeeded)) {
            continue;
          }

          loadedRequests.push(requestId);
        }
      }

      // If there are no pending requests, automatically fetch the next
      // unfetched chunk of the PDF
      if (!this.disableAutoFetch && isEmptyObj(this.requestsByChunk)) {
        var nextEmptyChunk;
        if (this.stream.numChunksLoaded === 1) {
          // This is a special optimization so that after fetching the first
          // chunk, rather than fetching the second chunk, we fetch the last
          // chunk.
          var lastChunk = this.stream.numChunks - 1;
          if (!this.stream.hasChunk(lastChunk)) {
            nextEmptyChunk = lastChunk;
          }
        } else {
          nextEmptyChunk = this.stream.nextEmptyChunk(endChunk);
        }
        if (isInt(nextEmptyChunk)) {
          this.requestChunks([nextEmptyChunk]);
        }
      }

      for (i = 0; i < loadedRequests.length; ++i) {
        requestId = loadedRequests[i];
        var callback = this.callbacksByRequest[requestId];
        delete this.callbacksByRequest[requestId];
        if (callback) {
          callback();
        }
      }

      this.msgHandler.send('DocProgress', {
        loaded: this.stream.numChunksLoaded * this.chunkSize,
        total: this.length
      });
    },

    onError: function ChunkedStreamManager_onError(err) {
      this._loadedStreamCapability.reject(err);
    },

    getBeginChunk: function ChunkedStreamManager_getBeginChunk(begin) {
      var chunk = Math.floor(begin / this.chunkSize);
      return chunk;
    },

    getEndChunk: function ChunkedStreamManager_getEndChunk(end) {
      if (end % this.chunkSize === 0) {
        return end / this.chunkSize;
      }

      // 0 -> 0
      // 1 -> 1
      // 99 -> 1
      // 100 -> 1
      // 101 -> 2
      var chunk = Math.floor((end - 1) / this.chunkSize) + 1;
      return chunk;
    }
  };

  return ChunkedStreamManager;
})();
