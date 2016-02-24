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

var EditSession = require("./edit_session").EditSession;
var JavaScriptMode = require("./mode/javascript").Mode;
var TokenIterator = require("./token_iterator").TokenIterator;
var assert = require("./test/assertions");

module.exports = {
    "test: token iterator initialization in JavaScript document" : function() {
        var lines = [
            "function foo(items) {",
            "    for (var i=0; i<items.length; i++) {",
            "        alert(items[i] + \"juhu\");",
            "    } // Real Tab.",
            "}"
        ];
        var session = new EditSession(lines.join("\n"), new JavaScriptMode());

        var iterator = new TokenIterator(session, 0, 0);
        assert.equal(iterator.getCurrentToken().value, "function");
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        iterator.stepForward();
        assert.equal(iterator.getCurrentToken().value, " ");
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 8);

        var iterator = new TokenIterator(session, 0, 4);
        assert.equal(iterator.getCurrentToken().value, "function");
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        iterator.stepForward();
        assert.equal(iterator.getCurrentToken().value, " ");
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 8);

        var iterator = new TokenIterator(session, 2, 18);
        assert.equal(iterator.getCurrentToken().value, "items");
        assert.equal(iterator.getCurrentTokenRow(), 2);
        assert.equal(iterator.getCurrentTokenColumn(), 14);

        iterator.stepForward();
        assert.equal(iterator.getCurrentToken().value, "[");
        assert.equal(iterator.getCurrentTokenRow(), 2);
        assert.equal(iterator.getCurrentTokenColumn(), 19);

        var iterator = new TokenIterator(session, 4, 0);
        assert.equal(iterator.getCurrentToken().value, "}");
        assert.equal(iterator.getCurrentTokenRow(), 4);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        iterator.stepBackward();
        assert.equal(iterator.getCurrentToken().value, "// Real Tab.");
        assert.equal(iterator.getCurrentTokenRow(), 3);
        assert.equal(iterator.getCurrentTokenColumn(), 6);

        var iterator = new TokenIterator(session, 5, 0);
        assert.equal(iterator.getCurrentToken(), null);
    },

    "test: token iterator initialization in text document" : function() {
        var lines = [
            "Lorem ipsum dolor sit amet, consectetur adipisicing elit,",
            "sed do eiusmod tempor incididunt ut labore et dolore magna",
            "aliqua. Ut enim ad minim veniam, quis nostrud exercitation",
            "ullamco laboris nisi ut aliquip ex ea commodo consequat."
        ];
        var session = new EditSession(lines.join("\n"));

        var iterator = new TokenIterator(session, 0, 0);
        assert.equal(iterator.getCurrentToken().value, lines[0]);
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        var iterator = new TokenIterator(session, 0, 4);
        assert.equal(iterator.getCurrentToken().value, lines[0]);
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        var iterator = new TokenIterator(session, 2, 18);
        assert.equal(iterator.getCurrentToken().value, lines[2]);
        assert.equal(iterator.getCurrentTokenRow(), 2);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        var iterator = new TokenIterator(session, 3, lines[3].length-1);
        assert.equal(iterator.getCurrentToken().value, lines[3]);
        assert.equal(iterator.getCurrentTokenRow(), 3);
        assert.equal(iterator.getCurrentTokenColumn(), 0);

        var iterator = new TokenIterator(session, 4, 0);
        assert.equal(iterator.getCurrentToken(), null);
    },

    "test: token iterator step forward in JavaScript document" : function() {
        var lines = [
            "function foo(items) {",
            "    for (var i=0; i<items.length; i++) {",
            "        alert(items[i] + \"juhu\");",
            "    } // Real Tab.",
            "}"
        ];
        var session = new EditSession(lines.join("\n"), new JavaScriptMode());

        var tokens = [];
        var len = session.getLength();
        for (var i = 0; i < len; i++)
            tokens = tokens.concat(session.getTokens(i));

        var iterator = new TokenIterator(session, 0, 0);
        for (var i = 1; i < tokens.length; i++)
            assert.equal(iterator.stepForward(), tokens[i]);
        assert.equal(iterator.stepForward(), null);
        assert.equal(iterator.getCurrentToken(), null);
    },

    "test: token iterator step backward in JavaScript document" : function() {
        var lines = [
            "function foo(items) {",
            "     for (var i=0; i<items.length; i++) {",
            "         alert(items[i] + \"juhu\");",
            "     } // Real Tab.",
            "}"
        ];
        var session = new EditSession(lines.join("\n"), new JavaScriptMode());

        var tokens = [];
        var len = session.getLength();
        for (var i = 0; i < len; i++)
            tokens = tokens.concat(session.getTokens(i));

        var iterator = new TokenIterator(session, 4, 0);
        for (var i = tokens.length-2; i >= 0; i--)
            assert.equal(iterator.stepBackward(), tokens[i]);
        assert.equal(iterator.stepBackward(), null);
        assert.equal(iterator.getCurrentToken(), null);
    },

    "test: token iterator reports correct row and column" : function() {
        var lines = [
            "function foo(items) {",
            "    for (var i=0; i<items.length; i++) {",
            "        alert(items[i] + \"juhu\");",
            "    } // Real Tab.",
            "}"
        ];
        var session = new EditSession(lines.join("\n"), new JavaScriptMode());

        var iterator = new TokenIterator(session, 0, 0);

        iterator.stepForward();
        iterator.stepForward();

        assert.equal(iterator.getCurrentToken().value, "foo");
        assert.equal(iterator.getCurrentTokenRow(), 0);
        assert.equal(iterator.getCurrentTokenColumn(), 9);

        iterator.stepForward();
        iterator.stepForward();
        iterator.stepForward();
        iterator.stepForward();
        iterator.stepForward();
        iterator.stepForward();
        iterator.stepForward();

        assert.equal(iterator.getCurrentToken().value, "for");
        assert.equal(iterator.getCurrentTokenRow(), 1);
        assert.equal(iterator.getCurrentTokenColumn(), 4);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
