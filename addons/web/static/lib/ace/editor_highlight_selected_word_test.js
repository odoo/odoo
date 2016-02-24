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
    require("./test/mockdom");
}

define(function(require, exports, module) {
"use strict";

var EditSession = require("./edit_session").EditSession;
var Editor = require("./editor").Editor;
var MockRenderer = require("./test/mockrenderer").MockRenderer;
var assert = require("./test/assertions");

var lipsum = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
             "Mauris at arcu mi, eu lobortis mauris. Quisque ut libero eget " +
             "diam congue vehicula. Quisque ut odio ut mi aliquam tincidunt. " +
             "Duis lacinia aliquam lorem eget eleifend. Morbi eget felis mi. " +
             "Duis quam ligula, consequat vitae convallis volutpat, blandit " +
             "nec neque. Nulla facilisi. Etiam suscipit lorem ac justo " +
             "sollicitudin tristique. Phasellus ut posuere nunc. Aliquam " +
             "scelerisque mollis felis non gravida. Vestibulum lacus sem, " +
             "posuere non bibendum id, luctus non dolor. Aenean id metus " +
             "lorem, vel dapibus est. Donec gravida feugiat augue nec " +
             "accumsan.Lorem ipsum dolor sit amet, consectetur adipiscing " +
             "elit. Nulla vulputate, velit vitae tincidunt congue, nunc " +
             "augue accumsan velit, eu consequat turpis lectus ac orci. " +
             "Pellentesque ornare dolor feugiat dui auctor eu varius nulla " +
             "fermentum. Sed aliquam odio at velit lacinia vel fermentum " +
             "felis sodales. In dignissim magna eget nunc lobortis non " +
             "fringilla nibh ullamcorper. Donec facilisis malesuada elit " +
             "at egestas. Etiam bibendum, diam vitae tempor aliquet, dui " +
             "libero vehicula odio, eget bibendum mauris velit eu lorem.\n" +
             "consectetur";

function callHighlighterUpdate(session, firstRow, lastRow) {
    var rangeCount = 0;
    var  mockMarkerLayer = { drawSingleLineMarker: function() {rangeCount++;} }
    session.$searchHighlight.update([], mockMarkerLayer, session, {
        firstRow: firstRow,
        lastRow: lastRow
    });
    return rangeCount;
}

module.exports = {
    setUp: function(next) {
        this.session = new EditSession(lipsum);
        this.editor = new Editor(new MockRenderer(), this.session);
        this.selection = this.session.getSelection();
        this.search = this.editor.$search;
        next();
    },

    "test: highlight selected words by default": function() {
        assert.equal(this.editor.getHighlightSelectedWord(), true);
    },

    "test: highlight a word": function() {
        this.editor.moveCursorTo(0, 9);
        this.selection.selectWord();

        var highlighter = this.editor.session.$searchHighlight;
        assert.ok(highlighter != null);

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "ipsum");
        assert.equal(highlighter.cache.length, 0);
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 2);
    },

    "test: highlight a word and clear highlight": function() {
        this.editor.moveCursorTo(0, 8);
        this.selection.selectWord();

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "ipsum");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 2);

        this.session.highlight("");
        assert.equal(this.session.$searchHighlight.cache.length, 0);
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 0);
    },

    "test: highlight another word": function() {
        this.selection.moveCursorTo(0, 14);
        this.selection.selectWord();

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "dolor");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 4);
    },

    "test: no selection, no highlight": function() {
        this.selection.clearSelection();
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 0);
    },

    "test: select a word, no highlight": function() {
        this.selection.moveCursorTo(0, 14);
        this.selection.selectWord();

        this.editor.setHighlightSelectedWord(false);

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "dolor");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 0);
    },

    "test: select a word with no matches": function() {
        this.editor.setHighlightSelectedWord(true);

        var currentOptions = this.search.getOptions();
        var newOptions = {
            wrap: true,
            wholeWord: true,
            caseSensitive: true,
            needle: "Mauris"
        };
        this.search.set(newOptions);

        var match = this.search.find(this.session);
        assert.notEqual(match, null, "found a match for 'Mauris'");

        this.search.set(currentOptions);

        this.selection.setSelectionRange(match);

        assert.equal(this.session.getTextRange(match), "Mauris");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 1);
    },

    "test: partial word selection 1": function() {
        this.selection.moveCursorTo(0, 14);
        this.selection.selectWord();
        this.selection.selectLeft();

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "dolo");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 0);
    },

    "test: partial word selection 2": function() {
        this.selection.moveCursorTo(0, 13);
        this.selection.selectWord();
        this.selection.selectRight();

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "dolor ");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 0);
    },

    "test: partial word selection 3": function() {
        this.selection.moveCursorTo(0, 14);
        this.selection.selectWord();
        this.selection.selectLeft();
        this.selection.shiftSelection(1);

        var range = this.selection.getRange();
        assert.equal(this.session.getTextRange(range), "olor");
        assert.equal(callHighlighterUpdate(this.session, 0, 0), 0);
    },

    "test: select last word": function() {
        this.selection.moveCursorTo(0, 1);

        var currentOptions = this.search.getOptions();
        var newOptions = {
            wrap: true,
            wholeWord: true,
            caseSensitive: true,
            backwards: true,
            needle: "consectetur"
        };
        this.search.set(newOptions);

        var match = this.search.find(this.session);
        assert.notEqual(match, null, "found a match for 'consectetur'");
        assert.position(match.start, 1, 0);

        this.search.set(currentOptions);

        this.selection.setSelectionRange(match);

        assert.equal(this.session.getTextRange(match), "consectetur");
        assert.equal(callHighlighterUpdate(this.session, 0, 1), 3);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
