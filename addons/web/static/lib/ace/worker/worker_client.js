/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2010, Ajax.org B.V.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of Ajax.org B.V. nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL AJAX.ORG B.V. BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ***** END LICENSE BLOCK ***** */

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var net = require("../lib/net");
var EventEmitter = require("../lib/event_emitter").EventEmitter;
var config = require("../config");

var WorkerClient = function(topLevelNamespaces, mod, classname, workerUrl) {
    this.$sendDeltaQueue = this.$sendDeltaQueue.bind(this);
    this.changeListener = this.changeListener.bind(this);
    this.onMessage = this.onMessage.bind(this);

    // nameToUrl is renamed to toUrl in requirejs 2
    if (require.nameToUrl && !require.toUrl)
        require.toUrl = require.nameToUrl;
    
    if (config.get("packaged") || !require.toUrl) {
        workerUrl = workerUrl || config.moduleUrl(mod, "worker");
    } else {
        var normalizePath = this.$normalizePath;
        workerUrl = workerUrl || normalizePath(require.toUrl("ace/worker/worker.js", null, "_"));

        var tlns = {};
        topLevelNamespaces.forEach(function(ns) {
            tlns[ns] = normalizePath(require.toUrl(ns, null, "_").replace(/(\.js)?(\?.*)?$/, ""));
        });
    }

    try {
        this.$worker = new Worker(workerUrl);
    } catch(e) {
        if (e instanceof window.DOMException) {
            // Likely same origin problem. Use importScripts from a shim Worker
            var blob = this.$workerBlob(workerUrl);
            var URL = window.URL || window.webkitURL;
            var blobURL = URL.createObjectURL(blob);

            this.$worker = new Worker(blobURL);
            URL.revokeObjectURL(blobURL);
        } else {
            throw e;
        }
    }
    this.$worker.postMessage({
        init : true,
        tlns : tlns,
        module : mod,
        classname : classname
    });

    this.callbackId = 1;
    this.callbacks = {};

    this.$worker.onmessage = this.onMessage;
};

(function(){

    oop.implement(this, EventEmitter);

    this.onMessage = function(e) {
        var msg = e.data;
        switch(msg.type) {
            case "event":
                this._signal(msg.name, {data: msg.data});
                break;
            case "call":
                var callback = this.callbacks[msg.id];
                if (callback) {
                    callback(msg.data);
                    delete this.callbacks[msg.id];
                }
                break;
            case "error":
                this.reportError(msg.data);
                break;
            case "log":
                window.console && console.log && console.log.apply(console, msg.data);
                break;
        }
    };
    
    this.reportError = function(err) {
        window.console && console.error && console.error(err);
    };

    this.$normalizePath = function(path) {
        return net.qualifyURL(path);
    };

    this.terminate = function() {
        this._signal("terminate", {});
        this.deltaQueue = null;
        this.$worker.terminate();
        this.$worker = null;
        if (this.$doc)
            this.$doc.off("change", this.changeListener);
        this.$doc = null;
    };

    this.send = function(cmd, args) {
        this.$worker.postMessage({command: cmd, args: args});
    };

    this.call = function(cmd, args, callback) {
        if (callback) {
            var id = this.callbackId++;
            this.callbacks[id] = callback;
            args.push(id);
        }
        this.send(cmd, args);
    };

    this.emit = function(event, data) {
        try {
            // firefox refuses to clone objects which have function properties
            // TODO: cleanup event
            this.$worker.postMessage({event: event, data: {data: data.data}});
        }
        catch(ex) {
            console.error(ex.stack);
        }
    };

    this.attachToDocument = function(doc) {
        if(this.$doc)
            this.terminate();

        this.$doc = doc;
        this.call("setValue", [doc.getValue()]);
        doc.on("change", this.changeListener);
    };

    this.changeListener = function(delta) {
        if (!this.deltaQueue) {
            this.deltaQueue = [];
            setTimeout(this.$sendDeltaQueue, 0);
        }
        if (delta.action == "insert")
            this.deltaQueue.push(delta.start, delta.lines);
        else
            this.deltaQueue.push(delta.start, delta.end);
    };

    this.$sendDeltaQueue = function() {
        var q = this.deltaQueue;
        if (!q) return;
        this.deltaQueue = null;
        if (q.length > 50 && q.length > this.$doc.getLength() >> 1) {
            this.call("setValue", [this.$doc.getValue()]);
        } else
            this.emit("change", {data: q});
    };

    this.$workerBlob = function(workerUrl) {
        // workerUrl can be protocol relative
        // importScripts only takes fully qualified urls
        var script = "importScripts('" + net.qualifyURL(workerUrl) + "');";
        try {
            return new Blob([script], {"type": "application/javascript"});
        } catch (e) { // Backwards-compatibility
            var BlobBuilder = window.BlobBuilder || window.WebKitBlobBuilder || window.MozBlobBuilder;
            var blobBuilder = new BlobBuilder();
            blobBuilder.append(script);
            return blobBuilder.getBlob("application/javascript");
        }
    };

}).call(WorkerClient.prototype);


var UIWorkerClient = function(topLevelNamespaces, mod, classname) {
    this.$sendDeltaQueue = this.$sendDeltaQueue.bind(this);
    this.changeListener = this.changeListener.bind(this);
    this.callbackId = 1;
    this.callbacks = {};
    this.messageBuffer = [];

    var main = null;
    var emitSync = false;
    var sender = Object.create(EventEmitter);
    var _self = this;

    this.$worker = {};
    this.$worker.terminate = function() {};
    this.$worker.postMessage = function(e) {
        _self.messageBuffer.push(e);
        if (main) {
            if (emitSync)
                setTimeout(processNext);
            else
                processNext();
        }
    };
    this.setEmitSync = function(val) { emitSync = val };

    var processNext = function() {
        var msg = _self.messageBuffer.shift();
        if (msg.command)
            main[msg.command].apply(main, msg.args);
        else if (msg.event)
            sender._signal(msg.event, msg.data);
    };

    sender.postMessage = function(msg) {
        _self.onMessage({data: msg});
    };
    sender.callback = function(data, callbackId) {
        this.postMessage({type: "call", id: callbackId, data: data});
    };
    sender.emit = function(name, data) {
        this.postMessage({type: "event", name: name, data: data});
    };

    config.loadModule(["worker", mod], function(Main) {
        main = new Main[classname](sender);
        while (_self.messageBuffer.length)
            processNext();
    });
};

UIWorkerClient.prototype = WorkerClient.prototype;

exports.UIWorkerClient = UIWorkerClient;
exports.WorkerClient = WorkerClient;

});
