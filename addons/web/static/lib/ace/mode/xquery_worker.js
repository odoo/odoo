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
var Mirror = require("../worker/mirror").Mirror;
var XQLintLib = require("./xquery/xqlint");
var XQLint =  XQLintLib.XQLint;

var getModuleResolverFromModules = function(modules){
    return function(uri){
            var index = modules;
            var mod = index[uri];
            var variables = {};
            var functions = {};
            mod.functions.forEach(function(fn){
                functions[uri + '#' + fn.name + '#' + fn.arity] = {
                    params: []
                };
                fn.parameters.forEach(function(param){
                    functions[uri + '#' + fn.name + '#' + fn.arity].params.push('$' + param.name);
                });
            });
            mod.variables.forEach(function(variable){
                var name = variable.name.substring(variable.name.indexOf(':') + 1);
                variables[uri + '#' + name] = { type: 'VarDecl', annotations: [] };
            });
            return {
                variables: variables,
                functions: functions
            };
    };
};

var XQueryWorker = exports.XQueryWorker = function(sender) {
    Mirror.call(this, sender);
    this.setTimeout(200);
    this.opts = {
        styleCheck: false
    };
    //this.availableModuleNamespaces = Object.keys(Modules);
    //this.moduleResolver; = getModuleResolverFromModules(Modules);
    var that = this;

    this.sender.on("complete", function(e){
        if(that.xqlint) {
            var pos = { line: e.data.pos.row, col: e.data.pos.column };
            var proposals = that.xqlint.getCompletions(pos);
            that.sender.emit("complete", proposals);
        }
    });

    this.sender.on("setAvailableModuleNamespaces", function(e){
        that.availableModuleNamespaces = e.data;
    });

    this.sender.on("setModuleResolver", function(e){
        that.moduleResolver = getModuleResolverFromModules(e.data);
    });
};

oop.inherits(XQueryWorker, Mirror);

(function() {
    
    this.onUpdate = function() {
        this.sender.emit("start");
        var value = this.doc.getValue();
        var sctx = XQLintLib.createStaticContext();
        if(this.moduleResolver) {
            sctx.setModuleResolver(this.moduleResolver);
        }
        if(this.availableModuleNamespaces) {
            sctx.availableModuleNamespaces = this.availableModuleNamespaces;
        }
        var opts = {
            styleCheck: this.styleCheck,
            staticContext: sctx
        };
        this.xqlint = new XQLint(value, opts);
        this.sender.emit("markers", this.xqlint.getMarkers());
    };
}).call(XQueryWorker.prototype);

});
