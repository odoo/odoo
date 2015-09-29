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

// The loading of ace/worker/worker is complicated, because when we need to load
// it via RequireJS, it needs a shim to make it into a AMD-module.
// When using the AMD-loader it's just works, so we just it load the file now

require("amd-loader");

define(function(require, exports, module) {
"use strict";

var assert = require("../test/assertions");
var worker = require("./worker")

module.exports = {
    setUp : function() {
        // And define a few mock dependency modules
        worker.define("depA", [], function(require, exports, module) {
            module.exports = 'dependency A';
        })
        worker.define("depB", [], function(require, exports, module) {
            module.exports = 'dependency B';
        })
    },

    "test: define() with no dependencies, and CommonJS-compatability require()-calls" : function() {
        // We want to be able to call define without an id or deps, but
        // since we aren't loading an external file, we must explicitly give
        // it some kind of id, in this case 'test1'.
        worker.require.id = 'test1';
        // Now define out module
        worker.define(function(require, exports, module) {
            var depA = require("depA");
            var depB = require("depB");
            assert.equal("dependency A", depA);
            assert.equal("dependency B", depB);
            module.exports = 'test 1';
        })
        // And then try and require it
        var res = worker.require("test1")
        assert.equal("test 1", res)
    },
    "test: define() with dependencies" : function() {
        // We want to be able to call define without an id, but since we aren't
        // loading an external file, we must explicitly give it some kind of
        // id, in this case 'test2'.
        worker.require.id = 'test2';
        // Now define our module
        worker.define(['depA', 'depB'], function(depA, depB) {
            assert.equal("dependency A", depA);
            assert.equal("dependency B", depB);
            return 'test 2';
        })
        // And then try and require it
        var res = worker.require("test2");
        assert.equal("test 2", res);
    },
    "test: define() used require, exports and module as a dependency": function() {
        // We want to be able to call define without an id, but since we aren't
        // loading an external file, we must explicitly give it some kind of
        // id, in this case 'test3'.
        worker.require.id = 'test3';
        // Now define our module
        worker.define(['require', 'exports', 'module', 'depA', 'depB'], function(require, exports, module) {
            var depA = require("depA");
            var depB = require("depB");
            assert.equal("dependency A", depA);
            assert.equal("dependency B", depB);
            module.exports = 'test 3';
        })
        // And then try and require it
        var res = worker.require("test3");
        assert.equal("test 3", res);
    },
    "test: define() with a mix of require and actual dependecies": function() {
        // We want to be able to call define without an id, but since we aren't
        // loading an external file, we must explicitly give it some kind of
        // id, in this case 'test4'.
        worker.require.id = 'test4';
        // Now define our module
        worker.define(['depA', 'require'], function(depA, require) {
            var depB = require("depB");
            assert.equal("dependency A", depA);
            assert.equal("dependency B", depB);
            return 'test 4';
        })
        // And then try and require it
        var res = worker.require("test4");
        assert.equal("test 4", res);
    }
}

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}