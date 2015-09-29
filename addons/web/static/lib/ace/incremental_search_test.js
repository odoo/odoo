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

var emacs = require('./keyboard/emacs');
var EditSession = require("./edit_session").EditSession;
var Editor = require("./editor").Editor;
var MockRenderer = require("./test/mockrenderer").MockRenderer;
var Range = require("./range").Range;
var MultiSelect = require("./multi_select").MultiSelect;
var assert = require("./test/assertions");
var IncrementalSearch = require("./incremental_search").IncrementalSearch;

require("./multi_select");

var editor, iSearch;
function testRanges(str, ranges) {
    ranges = ranges || editor.selection.getAllRanges();
    assert.equal(ranges + "", str + "");
}

// force "rerender"
function callHighlighterUpdate() {
    var session = editor.session,
        ranges = [],
        mockMarkerLayer = {
            drawSingleLineMarker: function(_, markerRanges) {
                ranges = ranges.concat(markerRanges);
            }
        }
    session.$isearchHighlight.update([], mockMarkerLayer, session, {
        firstRow: 0, lastRow: session.getRowLength()});
    return ranges;
}

module.exports = {

    name: "ACE incremental_search.js",

    setUp: function() {
        var session = new EditSession(["abc123", "xyz124"]);
        editor = new Editor(new MockRenderer(), session);
        new MultiSelect(editor);
        iSearch = new IncrementalSearch();
    },

    "test: keyboard handler setup" : function() {
        iSearch.activate(editor);
        assert.equal(editor.getKeyboardHandler(), iSearch.$keyboardHandler);
        iSearch.deactivate();
        assert.notEqual(editor.getKeyboardHandler(), iSearch.$keyboardHandler);
    },

    "test: isearch highlight setup" : function() {
        var sess = editor.session;
        iSearch.activate(editor);
        iSearch.highlight('foo');
        var highl = sess.$isearchHighlight.id;
        assert.ok(sess.$isearchHighlight, 'session has no isearch highlighter');
        assert.equal(sess.getMarkers()[highl.id], highl.id, 'isearch highlight not in markers');
        iSearch.deactivate();
        iSearch.activate(editor);
        iSearch.highlight('bar');
        var highl2 = sess.$isearchHighlight.id;
        assert.equal(highl2, highl, 'multiple isearch highlights');
    },

    "test: find simple text incrementally" : function() {
        iSearch.activate(editor);
        var range = iSearch.addString('1'), // "1"
            highlightRanges = callHighlighterUpdate(editor.session);
        testRanges("Range: [0/3] -> [0/4]", [range], "range");
        testRanges("Range: [0/3] -> [0/4],Range: [1/3] -> [1/4]", highlightRanges, "highlight");

        range = iSearch.addString('2'); // "12"
        highlightRanges = callHighlighterUpdate(editor.session);
        testRanges("Range: [0/3] -> [0/5]", [range], "range");
        testRanges("Range: [0/3] -> [0/5],Range: [1/3] -> [1/5]", highlightRanges, "highlight");

        range = iSearch.addString('3'); // "123"
        highlightRanges = callHighlighterUpdate(editor.session);
        testRanges("Range: [0/3] -> [0/6]", [range], "range");
        testRanges("Range: [0/3] -> [0/6]", highlightRanges, "highlight");

        range = iSearch.removeChar(); // "12"
        highlightRanges = callHighlighterUpdate(editor.session);
        testRanges("Range: [0/3] -> [0/5]", [range], "range");
        testRanges("Range: [0/3] -> [0/5],Range: [1/3] -> [1/5]", highlightRanges, "highlight");
    },

    "test: forward / backward" : function() {
        iSearch.activate(editor);
        iSearch.addString('1'); iSearch.addString('2');
        var range = iSearch.next();
        testRanges("Range: [1/3] -> [1/5]", [range], "range");

        range = iSearch.next(); // nothing to find
        testRanges("", [range], "range");

        range = iSearch.next({backwards: true}); // backwards
        testRanges("Range: [1/5] -> [1/3]", [range], "range");
    },

    "test: cancelSearch" : function() {
        iSearch.activate(editor);
        iSearch.addString('1'); iSearch.addString('2');
        var range = iSearch.cancelSearch(true);
        testRanges("Range: [0/0] -> [0/0]", [range], "range");

        iSearch.addString('1'); range = iSearch.addString('2');
        testRanges("Range: [0/3] -> [0/5]", [range], "range");
    },

    "test: failing search keeps pos" : function() {
        iSearch.activate(editor);
        iSearch.addString('1'); iSearch.addString('2');
        var range = iSearch.addString('x');
        testRanges("", [range], "range");
        assert.position(editor.getCursorPosition(), 0, 5);
    },

    "test: backwards search" : function() {
        editor.moveCursorTo(1,0);
        iSearch.activate(editor, true);
        iSearch.addString('1'); var range = iSearch.addString('2');;
        testRanges("Range: [0/5] -> [0/3]", [range], "range");
        assert.position(editor.getCursorPosition(), 0, 3);
    },

    "test: forwards then backwards, same result, reoriented range" : function() {
        iSearch.activate(editor);
        iSearch.addString('1'); var range = iSearch.addString('2');;
        testRanges("Range: [0/3] -> [0/5]", [range], "range");
        assert.position(editor.getCursorPosition(), 0, 5);

        range = iSearch.next({backwards: true});
        testRanges("Range: [0/5] -> [0/3]", [range], "range");
        assert.position(editor.getCursorPosition(), 0, 3);
    },

    "test: reuse prev search via option" : function() {
        iSearch.activate(editor);
        iSearch.addString('1'); iSearch.addString('2');;
        assert.position(editor.getCursorPosition(), 0, 5);
        iSearch.deactivate();

        iSearch.activate(editor);
        iSearch.next({backwards: false, useCurrentOrPrevSearch: true});
        assert.position(editor.getCursorPosition(), 1, 5);
    },

    "test: don't extend selection range if selection is empty" : function() {
        iSearch.activate(editor);
        iSearch.addString('1'); iSearch.addString('2');;
        testRanges("Range: [0/5] -> [0/5]", [editor.getSelectionRange()], "sel range");
    },

    "test: extend selection range if selection exists" : function() {
        iSearch.activate(editor);
        editor.selection.selectTo(0, 1);
        iSearch.addString('1'); iSearch.addString('2');;
        testRanges("Range: [0/0] -> [0/5]", [editor.getSelectionRange()], "sel range");
    },

    "test: extend selection in emacs mark mode" : function() {
        var emacs = require('./keyboard/emacs');
        editor.keyBinding.addKeyboardHandler(emacs.handler);
        emacs.handler.commands.setMark.exec(editor);
        iSearch.activate(editor);
        iSearch.addString('1'); iSearch.addString('2');
        testRanges("Range: [0/0] -> [0/5]", [editor.getSelectionRange()], "sel range");
    }

};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
