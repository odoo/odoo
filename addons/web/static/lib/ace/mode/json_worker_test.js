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

var assert = require("../test/assertions");
var Worker = require("./json_worker").JsonWorker;


module.exports = {
    setUp : function() {
        this.sender = {
            on: function() {},
            callback: function(data, id) {
                this.data = data;
            },
            events: [],
            emit: function(type, e) {
                this.events.push([type, e]);
            }
        };
    },

    "test check valid json": function() {
        var worker = new Worker(this.sender);
        worker.setValue("{}");
        worker.deferredUpdate.call();

        assert.equal(this.sender.events[0][1].length, 0);
    },

    "test check for syntax error": function() {
        var worker = new Worker(this.sender);
        worker.setValue([
            "{",
            "juhu: 12",
            "}"
        ].join("\n"));
        worker.deferredUpdate.call();

        var event = this.sender.events[0];
        assert.equal(event[0], "annotate");
        assert.equal(event[1].length, 1);
        assert.equal(event[1][0].type, "error");
        assert.equal(event[1][0].text, "Bad string");
        assert.equal(event[1][0].row, 1);
        assert.equal(event[1][0].column, 0);

    },

    "test check for syntax error at first char": function() {
        var worker = new Worker(this.sender);
        worker.setValue("x");
        worker.deferredUpdate.call();

        var event = this.sender.events[0];
        assert.equal(event[0], "annotate");
        assert.equal(event[1][0].type, "error");
        assert.equal(event[1][0].text, "Unexpected 'x'");
        assert.equal(event[1][0].row, 0);
        assert.equal(event[1][0].column, 0);
    }

};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
