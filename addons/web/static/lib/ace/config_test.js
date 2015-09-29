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

if (typeof process !== "undefined") {
    require("amd-loader");
}

define(function(require, exports, module) {
"use strict";

var config = require("./config");
var assert = require("./test/assertions");

module.exports = {

    "test: path resolution" : function() {
        config.set("packaged", "true");
        var url = config.moduleUrl("kr_theme", "theme");
        assert.equal(url, "theme-kr_theme.js");
        
        config.set("basePath", "a/b");
        url = config.moduleUrl("m/theme", "theme");
        assert.equal(url, "a/b/theme-m.js");
        
        url = config.moduleUrl("m/theme", "ext");
        assert.equal(url, "a/b/ext-theme.js");
        
        config.set("workerPath", "c/");
        url = config.moduleUrl("foo/1", "worker");
        assert.equal(url, "c/worker-1.js");
        
        config.setModuleUrl("foo/1", "a/b1.js");
        url = config.moduleUrl("foo/1", "theme");
        assert.equal(url, "a/b1.js");
        
        url = config.moduleUrl("snippets/js");
        assert.equal(url, "a/b/snippets/js.js");
        
        config.setModuleUrl("snippets/js", "_.js");
        url = config.moduleUrl("snippets/js");
        assert.equal(url, "_.js");
        
        url = config.moduleUrl("ace/ext/textarea");
        assert.equal(url, "a/b/ext-textarea.js");
        
        assert.equal();
    },
    "test: define options" : function() {
        var o = {};
        config.defineOptions(o, "test_object", {
            opt1: {
                set: function(val) {
                    this.x = val;
                },
                value: 7,
            },
            initialValue: {
                set: function(val) {
                    this.x = val;
                },
                initialValue: 8,
            },
            opt2: {
                get: function(val) {
                    return this.x;
                }
            },
            forwarded: "model"
        });
        o.model = {};
        config.defineOptions(o.model, "model", {
            forwarded: {value: 1}
        });
        
        config.resetOptions(o);
        config.resetOptions(o.model);
        assert.equal(o.getOption("opt1"), 7);
        assert.equal(o.getOption("opt2"), 7);
        o.setOption("opt1", 8);
        assert.equal(o.getOption("opt1"), 8);
        assert.equal(o.getOption("opt2"), 8);
        
        assert.equal(o.getOption("forwarded"), 1);
        
        assert.equal(o.getOption("new"), undefined);
        o.setOption("new", 0);
        assert.equal(o.getOption("new"), undefined);
        

        assert.equal(o.getOption("initialValue"), 8);
        o.setOption("initialValue", 7);
        assert.equal(o.getOption("opt2"), 7);
        
        config.setDefaultValues("test_object", {
            opt1: 1,
            forwarded: 2
        });
        config.resetOptions(o);
        assert.equal(o.getOption("opt1"), 1);
        assert.equal(o.getOption("forwarded"), 2);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
