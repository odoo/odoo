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

var assert = require("../../test/assertions");
var coffee = require("./coffee");

function assertLocation(e, sl, sc, el, ec) {
    var l = e.location;
    assert.equal(
        l.first_line + ":" + l.first_column + "->"  + l.last_line + ":" + l.last_column,
        sl + ":" + sc + "->"  + el + ":" + ec
    );
}

function parse(str) {
    try {
        coffee.compile(str);
    } catch (e) {
        return e;
    }
}

module.exports = {
    "test parse valid coffee script": function() {
        coffee.compile("square = (x) -> x * x");
    },
    
    "test parse invalid coffee script": function() {
        var e = parse("a = 12 f");
        assert.equal(e.message, "unexpected identifier");
        assertLocation(e, 0, 7, 0, 7);
    },
    
    "test parse missing bracket": function() {
        var e = parse("a = 12 f {\n\n");
        assert.equal(e.message, "missing }");
        assertLocation(e, 0, 9, 0, 9);
    },
    "test unexpected indent": function() {
        var e = parse("a\n  a\n");
        assert.equal(e.message, "unexpected indentation");
        assertLocation(e, 1, 0, 1, 1);
    },
    "test invalid destructuring": function() {
        var e = parse("\n{b: 5} = {}");
        assert.equal(e.message, '"5" cannot be assigned');
        assertLocation(e, 1, 4, 1, 4);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
