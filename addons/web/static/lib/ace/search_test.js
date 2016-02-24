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
var MockRenderer = require("./test/mockrenderer").MockRenderer;
var Editor = require("./editor").Editor;
var Search = require("./search").Search;
var assert = require("./test/assertions");

module.exports = {
    "test: configure the search object" : function() {
        var search = new Search();
        search.set({
            needle: "juhu"
        });
    },

    "test: find simple text in document" : function() {
        var session = new EditSession(["juhu kinners 123", "456"]);
        var search = new Search().set({
            needle: "kinners"
        });

        var range = search.find(session);
        assert.position(range.start, 0, 5);
        assert.position(range.end, 0, 12);
    },

    "test: find simple text in next line" : function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);
        var search = new Search().set({
            needle: "kinners"
        });

        var range = search.find(session);
        assert.position(range.start, 1, 5);
        assert.position(range.end, 1, 12);
    },

    "test: find text starting at cursor position" : function() {
        var session = new EditSession(["juhu kinners", "juhu kinners 123"]);
        session.getSelection().moveCursorTo(0, 6);
        var search = new Search().set({
            needle: "kinners"
        });

        var range = search.find(session);
        assert.position(range.start, 1, 5);
        assert.position(range.end, 1, 12);
    },

    "test: wrap search is on by default" : function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);
        session.getSelection().moveCursorTo(2, 1);

        var search = new Search().set({
            needle: "kinners"
        });

        assert.notEqual(search.find(session), null);
    },

    "test: wrap search should wrap at file end" : function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);
        session.getSelection().moveCursorTo(2, 1);

        var search = new Search().set({
            needle: "kinners",
            wrap: true
        });

        var range = search.find(session);
        assert.position(range.start, 1, 5);
        assert.position(range.end, 1, 12);
    },

    "test: wrap search should find needle even if it starts inside it" : function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);
        session.getSelection().moveCursorTo(6, 1);

        var search = new Search().set({
            needle: "kinners",
            wrap: true
        });

        var range = search.find(session);
        assert.position(range.start, 1, 5);
        assert.position(range.end, 1, 12);
    },

    "test: wrap search with no match should return 'null'": function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);
        session.getSelection().moveCursorTo(2, 1);

        var search = new Search().set({
            needle: "xyz",
            wrap: true
        });

        assert.equal(search.find(session), null);
    },

    "test: case sensitive is by default off": function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);

        var search = new Search().set({
            needle: "JUHU"
        });

        assert.range(search.find(session), 1, 0, 1, 4);
    },

    "test: case sensitive search": function() {
        var session = new EditSession(["abc", "juhu kinners 123", "456"]);

        var search = new Search().set({
            needle: "KINNERS",
            caseSensitive: true
        });

        var range = search.find(session);
        assert.equal(range, null);
    },

    "test: whole word search should not match inside of words": function() {
        var session = new EditSession(["juhukinners", "juhu kinners 123", "456"]);

        var search = new Search().set({
            needle: "kinners",
            wholeWord: true
        });

        var range = search.find(session);
        assert.position(range.start, 1, 5);
        assert.position(range.end, 1, 12);
    },

    "test: find backwards": function() {
        var session = new EditSession(["juhu juhu juhu juhu"]);
        session.getSelection().moveCursorTo(0, 10);
        var search = new Search().set({
            needle: "juhu",
            backwards: true
        });

        var range = search.find(session);
        assert.position(range.start, 0, 5);
        assert.position(range.end, 0, 9);
    },

    "test: find in selection": function() {
        var session = new EditSession(["juhu", "juhu", "juhu", "juhu"]);
        session.getSelection().setSelectionAnchor(1, 0);
        session.getSelection().selectTo(3, 5);

        var search = new Search().set({
            needle: "juhu",
            wrap: true,
            range: session.getSelection().getRange()
        });

        var range = search.find(session);
        assert.position(range.start, 1, 0);
        assert.position(range.end, 1, 4);

        search = new Search().set({
            needle: "juhu",
            wrap: true,
            range: session.getSelection().getRange()
        });

        session.getSelection().setSelectionAnchor(0, 2);
        session.getSelection().selectTo(3, 2);

        var range = search.find(session);
        assert.position(range.start, 1, 0);
        assert.position(range.end, 1, 4);
    },

    "test: find backwards in selection": function() {
        var session = new EditSession(["juhu", "juhu", "juhu", "juhu"]);

        session.getSelection().setSelectionAnchor(0, 2);
        session.getSelection().selectTo(3, 2);

        var search = new Search().set({
            needle: "juhu",
            wrap: true,
            backwards: true,
            range: session.getSelection().getRange()
        });

        var range = search.find(session);
        assert.position(range.start, 2, 0);
        assert.position(range.end, 2, 4);

        search = new Search().set({
            needle: "juhu",
            wrap: true,
            range: session.getSelection().getRange()
        });

        session.getSelection().setSelectionAnchor(0, 2);
        session.getSelection().selectTo(1, 2);

        var range = search.find(session);
        assert.position(range.start, 1, 0);
        assert.position(range.end, 1, 4);
    },

    "test: edge case - match directly before the cursor" : function() {
        var session = new EditSession(["123", "123", "juhu"]);

        var search = new Search().set({
            needle: "juhu",
            wrap: true
        });

        session.getSelection().moveCursorTo(2, 5);

        var range = search.find(session);
        assert.position(range.start, 2, 0);
        assert.position(range.end, 2, 4);
    },

    "test: edge case - match backwards directly after the cursor" : function() {
        var session = new EditSession(["123", "123", "juhu"]);

        var search = new Search().set({
            needle: "juhu",
            wrap: true,
            backwards: true
        });

        session.getSelection().moveCursorTo(2, 0);

        var range = search.find(session);
        assert.position(range.start, 2, 0);
        assert.position(range.end, 2, 4);
    },

    "test: find using a regular expression" : function() {
        var session = new EditSession(["abc123 123 cd", "abc"]);

        var search = new Search().set({
            needle: "\\d+",
            regExp: true
        });

        var range = search.find(session);
        assert.position(range.start, 0, 3);
        assert.position(range.end, 0, 6);
    },

    "test: find using a regular expression and whole word" : function() {
        var session = new EditSession(["abc123 123 cd", "abc"]);

        var search = new Search().set({
            needle: "\\d+\\b",
            regExp: true,
            wholeWord: true
        });

        var range = search.find(session);
        assert.position(range.start, 0, 7);
        assert.position(range.end, 0, 10);
    },

    "test: use regular expressions with capture groups": function() {
        var session = new EditSession(["  ab: 12px", "  <h1 abc"]);

        var search = new Search().set({
            needle: "(\\d+)",
            regExp: true
        });

        var range = search.find(session);
        assert.position(range.start, 0, 6);
        assert.position(range.end, 0, 8);
    },

    "test: find all matches in selection" : function() {
        var session = new EditSession(["juhu", "juhu", "juhu", "juhu"]);

        session.getSelection().setSelectionAnchor(0, 2);
        session.getSelection().selectTo(3, 2);

        var search = new Search().set({
            needle: "uh",
            wrap: true,
            range: session.getSelection().getRange()
        });

        var ranges = search.findAll(session);

        assert.equal(ranges.length, 2);
        assert.position(ranges[0].start, 1, 1);
        assert.position(ranges[0].end, 1, 3);
        assert.position(ranges[1].start, 2, 1);
        assert.position(ranges[1].end, 2, 3);
    },
    
    
    "test: find all multiline matches" : function() {
        var session = new EditSession(["juhu", "juhu", "juhu", "juhu"]);

        var search = new Search().set({
            needle: "hu\nju",
            wrap: true
        });

        var ranges = search.findAll(session);

        assert.equal(ranges.length, 3);
        assert.position(ranges[0].start, 0, 2);
        assert.position(ranges[0].end, 1, 2);
        assert.position(ranges[1].start, 1, 2);
        assert.position(ranges[1].end, 2, 2);
    },

    "test: replace() should return the replacement if the input matches the needle" : function() {
        var search = new Search().set({
            needle: "juhu"
        });

        assert.equal(search.replace("juhu", "kinners"), "kinners");
        assert.equal(search.replace("", "kinners"), null);
        assert.equal(search.replace(" juhu", "kinners"), null);

        // case sensitivity
        assert.equal(search.replace("Juhu", "kinners"), "kinners");
        search.set({caseSensitive: true});
        assert.equal(search.replace("Juhu", "kinners"), null);

        // regexp replacement
    },

    "test: replace with a RegExp search" : function() {
        var search = new Search().set({
            needle: "\\d+",
            regExp: true
        });

        assert.equal(search.replace("123", "kinners"), "kinners");
        assert.equal(search.replace("01234", "kinners"), "kinners");
        assert.equal(search.replace("", "kinners"), null);
        assert.equal(search.replace("a12", "kinners"), null);
        assert.equal(search.replace("12a", "kinners"), null);
    },

    "test: replace with RegExp match and capture groups" : function() {
        var search = new Search().set({
            needle: "ab(\\d\\d)",
            regExp: true
        });

        assert.equal(search.replace("ab12", "cd$1"), "cd12");
        assert.equal(search.replace("ab12", "-$&-"), "-ab12-");
        assert.equal(search.replace("ab12", "$$"), "$");
    },

    "test: find all using regular expresion containing $" : function() {
        var session = new EditSession(["a", "     b", "c ", "d"]);

        var search = new Search().set({
            needle: "[ ]+$",
            regExp: true,
            wrap: true
        });

        session.getSelection().moveCursorTo(1, 2);
        var ranges = search.findAll(session);

        assert.equal(ranges.length, 1);
        assert.position(ranges[0].start, 2, 1);
        assert.position(ranges[0].end, 2, 2);
    },

    "test: find all matches in a line" : function() {
        var session = new EditSession("foo bar foo baz foobar foo");

        var search = new Search().set({
            needle: "foo",
            wrap: true,
            wholeWord: true
        });

        session.getSelection().moveCursorTo(0, 4);

        var ranges = search.findAll(session);

        assert.equal(ranges.length, 3);
        assert.position(ranges[0].start, 0, 0);
        assert.position(ranges[0].end, 0, 3);
        assert.position(ranges[1].start, 0, 8);
        assert.position(ranges[1].end, 0, 11);
        assert.position(ranges[2].start, 0, 23);
        assert.position(ranges[2].end, 0, 26);
    },

    "test: find all matches in a line backwards" : function() {
        var session = new EditSession("foo bar foo baz foobar foo");

        var search = new Search().set({
            needle: "foo",
            wrap: true,
            wholeWord: true,
            backwards: true
        });

        session.getSelection().moveCursorTo(0, 13);

        var ranges = search.findAll(session);

        assert.equal(ranges.length, 3);
        assert.position(ranges[2].start, 0, 23);
        assert.position(ranges[2].end, 0, 26);
        assert.position(ranges[1].start, 0, 8);
        assert.position(ranges[1].end, 0, 11);
        assert.position(ranges[0].start, 0, 0);
        assert.position(ranges[0].end, 0, 3);
    },

    "test: find next empty range" : function() {
        var session = new EditSession("foo foobar foo");
        var editor = new Editor(new MockRenderer(), session);
        
        var options = {
            needle: "o*",
            wrap: true,
            regExp: true,
            backwards: false
        };
        var positions = [4, 5.2, 7, 8, 9, 10, 11, 12.2, 14, 0, 1.2, 3];
        
        session.selection.moveCursorTo(0, 3);
        for (var i = 0; i < 12; i++) {
            editor.find(options)
            var range = editor.selection.getRange();
            var start = range.start.column;
            var len = range.end.column - start;
            assert.equal(start + 0.1 * len, positions[i])
        }
        options.backwards = true;
        positions = [1.2, 1, 0, 14, 12.2, 12, 11, 10, 9, 8, 7, 5.2, 5, 4, 3];
        for (var i = 0; i < 16; i++) {
            editor.find(options);
            var range = editor.selection.getRange();
            var start = range.start.column;
            var len = range.end.column - start;
            console.log(start + 0.1 * len)
        }
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
