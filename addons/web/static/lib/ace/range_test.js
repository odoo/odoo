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

var Range = require("./range").Range;
var EditSession = require("./edit_session").EditSession;
var assert = require("./test/assertions");

module.exports = {
    
    name: "ACE range.js",
    
    "test: create range": function() {
        var range = new Range(1,2,3,4);

        assert.equal(range.start.row, 1);
        assert.equal(range.start.column, 2);
        assert.equal(range.end.row, 3);
        assert.equal(range.end.column, 4);
    },

    "test: create from points": function() {
        var range = Range.fromPoints({row: 1, column: 2}, {row:3, column:4});

        assert.equal(range.start.row, 1);
        assert.equal(range.start.column, 2);
        assert.equal(range.end.row, 3);
        assert.equal(range.end.column, 4);
    },

    "test: clip to rows": function() {
        assert.range(new Range(0, 20, 100, 30).clipRows(10, 30), 10, 0, 31, 0);
        assert.range(new Range(0, 20, 30, 10).clipRows(10, 30), 10, 0, 30, 10);

        var range = new Range(0, 20, 3, 10);
        var range = range.clipRows(10, 30);

        assert.ok(range.isEmpty());
        assert.range(range, 10, 0, 10, 0);
    },

    "test: isEmpty": function() {
        var range = new Range(1, 2, 1, 2);
        assert.ok(range.isEmpty());

        var range = new Range(1, 2, 1, 6);
        assert.notOk(range.isEmpty());
    },

    "test: is multi line": function() {
        var range = new Range(1, 2, 1, 6);
        assert.notOk(range.isMultiLine());

        var range = new Range(1, 2, 2, 6);
        assert.ok(range.isMultiLine());
    },

    "test: clone": function() {
        var range = new Range(1, 2, 3, 4);
        var clone = range.clone();

        assert.position(clone.start, 1, 2);
        assert.position(clone.end, 3, 4);

        clone.start.column = 20;
        assert.position(range.start, 1, 2);

        clone.end.column = 20;
        assert.position(range.end, 3, 4);
    },

    "test: contains for multi line ranges": function() {
        var range = new Range(1, 10, 5, 20);

        assert.ok(range.contains(1, 10));
        assert.ok(range.contains(2, 0));
        assert.ok(range.contains(3, 100));
        assert.ok(range.contains(5, 19));
        assert.ok(range.contains(5, 20));

        assert.notOk(range.contains(1, 9));
        assert.notOk(range.contains(0, 0));
        assert.notOk(range.contains(5, 21));
    },

    "test: contains for single line ranges": function() {
        var range = new Range(1, 10, 1, 20);

        assert.ok(range.contains(1, 10));
        assert.ok(range.contains(1, 15));
        assert.ok(range.contains(1, 20));

        assert.notOk(range.contains(0, 9));
        assert.notOk(range.contains(2, 9));
        assert.notOk(range.contains(1, 9));
        assert.notOk(range.contains(1, 21));
    },

    "test: extend range": function() {
        var range = new Range(2, 10, 2, 30);

        var range = range.extend(2, 5);
        assert.range(range, 2, 5, 2, 30);

        var range = range.extend(2, 35);
        assert.range(range, 2, 5, 2, 35);

        var range = range.extend(2, 15);
        assert.range(range, 2, 5, 2, 35);

        var range = range.extend(1, 4);
        assert.range(range, 1, 4, 2, 35);

        var range = range.extend(6, 10);
        assert.range(range, 1, 4, 6, 10);
    },

    "test: collapse rows" : function() {
        var range = new Range(0, 2, 1, 2);
        assert.range(range.collapseRows(), 0, 0, 1, 0);

        var range = new Range(2, 2, 3, 1);
        assert.range(range.collapseRows(), 2, 0, 3, 0);

        var range = new Range(2, 2, 3, 0);
        assert.range(range.collapseRows(), 2, 0, 2, 0);

        var range = new Range(2, 0, 2, 0);
        assert.range(range.collapseRows(), 2, 0, 2, 0);
    },
    
    "test: to screen range" : function() {
        var session = new EditSession([
            "juhu",
            "12\t\t34",
            "ぁぁa",
            "\t\t34"
        ]);
        
        var range = new Range(0, 0, 0, 3);
        assert.range(range.toScreenRange(session), 0, 0, 0, 3);
        
        var range = new Range(1, 1, 1, 3);
        assert.range(range.toScreenRange(session), 1, 1, 1, 4);
        
        var range = new Range(2, 1, 2, 2);
        assert.range(range.toScreenRange(session), 2, 2, 2, 4);

        var range = new Range(3, 0, 3, 4);
        assert.range(range.toScreenRange(session), 3, 0, 3, 10);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
