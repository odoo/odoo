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

require("./multi_select");
var assert = require("./test/assertions");
var Range = require("./range").Range;
var Editor = require("./editor").Editor;
var EditSession = require("./edit_session").EditSession;
var MockRenderer = require("./test/mockrenderer").MockRenderer;
var UndoManager = require("./undomanager").UndoManager;

var editor;
var exec = function(name, times, args) {
    do {
        editor.commands.exec(name, editor, args);
    } while(times --> 1);
};
var testRanges = function(str) {
    assert.equal(editor.selection.getAllRanges() + "", str + "");
};
function getSelection(editor) {
    var data = editor.multiSelect.toJSON();
    if (!data.length) data = [data];
    data = data.map(function(x) {
        var a, c;
        if (x.isBackwards) {
            a = x.end;
            c = x.start;
        } else {
            c = x.end;
            a = x.start;
        }
        return Range.comparePoints(a, c) 
            ? [a.row, a.column, c.row, c.column]
            : [a.row, a.column];
    });
    return data.length > 1 ? data : data[0];
}
function testSelection(editor, data) {
    assert.equal(getSelection(editor) + "", data + "");
}
function setSelection(editor, data) {
    if (typeof data[0] == "number")
        data = [data];
    editor.selection.fromJSON(data.map(function(x) {
        var start = {row: x[0], column: x[1]};
        var end = x.length == 2 ? start : {row: x[2], column: x[3]};
        var isBackwards = Range.comparePoints(start, end) > 0;
        return isBackwards ? {
            start: end,
            end: start,
            isBackwards: isBackwards
        } : {
            start: start,
            end: end,
            isBackwards: isBackwards
        };
    }));
}

module.exports = {

    name: "ACE multi_select.js",

    "test: multiselect editing": function() {
        var doc = new EditSession([
            "w1.w2",
            "    wtt.w",
            "    wtt.w"
        ]);
        editor = new Editor(new MockRenderer(), doc);

        editor.navigateFileEnd();
        exec("selectMoreBefore", 3);
        assert.ok(editor.inMultiSelectMode);
        assert.equal(editor.selection.getAllRanges().length, 4);

        var newLine = editor.session.getDocument().getNewLineCharacter();
        var copyText = "wwww".split("").join(newLine);
        assert.equal(editor.getCopyText(), copyText);
        exec("insertstring", 1, "a");
        exec("backspace", 2);
        assert.equal(editor.session.getValue(), "w1.w2\ntt\ntt");
        assert.equal(editor.selection.getAllRanges().length, 4);

        exec("selectall");
        assert.ok(!editor.inMultiSelectMode);
        //assert.equal(editor.selection.getAllRanges().length, 1);
    },

    "test: multiselect navigation": function() {
        var doc = new EditSession([
            "w1.w2",
            "    wtt.w",
            "    wtt.we"
        ]);
        editor = new Editor(new MockRenderer(), doc);

        editor.selectMoreLines(1);
        testRanges("Range: [0/0] -> [0/0],Range: [1/0] -> [1/0]");
        assert.ok(editor.inMultiSelectMode);

        exec("golinedown");
        exec("gotolineend");
        testRanges("Range: [1/9] -> [1/9],Range: [2/10] -> [2/10]");
        exec("selectwordleft");

        testRanges("Range: [1/8] -> [1/9],Range: [2/8] -> [2/10]");
        exec("golinedown", 2);
        assert.ok(!editor.inMultiSelectMode);
    },

    "test: multiselect session change": function() {
        var doc = new EditSession([
            "w1.w2",
            "    wtt.w",
            "    wtt.w"
        ]);
        editor = new Editor(new MockRenderer(), doc);

        editor.selectMoreLines(1);
        testRanges("Range: [0/0] -> [0/0],Range: [1/0] -> [1/0]");
        assert.ok(editor.inMultiSelectMode);

        var doc2 = new EditSession(["w1"]);
        editor.setSession(doc2);
        assert.ok(!editor.inMultiSelectMode);

        editor.setSession(doc);
        assert.ok(editor.inMultiSelectMode);
    },

    "test: multiselect addRange": function() {
        var doc = new EditSession([
            "w1.w2",
            "    wtt.w",
            "    wtt.w"
        ]);
        editor = new Editor(new MockRenderer(), doc);
        var selection = editor.selection;

        var range1 = new Range(0, 2, 0, 4);
        editor.selection.fromOrientedRange(range1);

        var range2 = new Range(0, 3, 0, 4);
        selection.addRange(range2);
        assert.ok(!editor.inMultiSelectMode);
        assert.ok(range2.isEqual(editor.selection.getRange()));

        var range3 = new Range(0, 1, 0, 1);
        selection.addRange(range3);
        assert.ok(editor.inMultiSelectMode);
        testRanges([range3, range2]);

        var range4 = new Range(0, 0, 4, 0);
        selection.addRange(range4);
        assert.ok(!editor.inMultiSelectMode);
    },

    "test: onPaste in command with multiselect": function() {
        var doc = new EditSession(["l1", "l2"]);
        editor = new Editor(new MockRenderer(), doc);
        editor.commands.addCommand({
            name: 'insertfoo',
            exec: function(ed) { ed.onPaste('foo'); },
            multiSelectAction: "forEach"
        });
        var selection = editor.selection;
        var range1 = new Range(0,2,0,2);
        var range2 = new Range(1,2,1,2);
        selection.fromOrientedRange(range1);
        selection.addRange(range2);
        editor.execCommand('insertfoo');
        assert.equal('l1foo\nl2foo', editor.getValue());
    },
    
    "test multiselect move lines": function() {
        editor = new Editor(new MockRenderer());
        
        editor.setValue("l1\nl2\nl3\nl4", -1);
        setSelection(editor, [[0,2],[1,2],[2,2],[3,2]]);
        
        exec("copylinesdown");
        assert.equal(editor.getValue(),"l1\nl1\nl2\nl2\nl3\nl3\nl4\nl4");
        testSelection(editor, [[1,2],[3,2],[5,2],[7,2]]);
        exec("copylinesup");
        assert.equal(editor.getValue(),"l1\nl1\nl1\nl2\nl2\nl2\nl3\nl3\nl3\nl4\nl4\nl4");
        testSelection(editor, [[1,2],[4,2],[7,2],[10,2]]);
        exec("removeline");
        assert.equal(editor.getValue(),"l1\nl1\nl2\nl2\nl3\nl3\nl4\nl4");
        testSelection(editor, [[1,0],[3,0],[5,0],[7,0]]);
        
        setSelection(editor, [[1,2],[1,1,1,0],[3,0,3,1],[5,0,5,1],[7,0,7,1]]);
        exec("copylinesdown");
        exec("copylinesup");
        assert.equal(editor.getValue(),"l1\nl1\nl1\nl1\nl2\nl2\nl2\nl2\nl3\nl3\nl3\nl3\nl4\nl4\nl4\nl4");
        testSelection(editor, [[2,2],[2,1,2,0],[6,0,6,1],[10,0,10,1],[14,0,14,1]]);
        
        exec("movelinesdown", 12);
        assert.equal(editor.getValue(),"l1\nl1\nl1\nl2\nl2\nl2\nl3\nl3\nl3\nl4\nl4\nl4\nl1\nl2\nl3\nl4");
        testSelection(editor, [[12,2],[12,1,12,0],[13,0,13,1],[14,0,14,1],[15,0,15,1]]);
        
        exec("movelinesup", 12);
        assert.equal(editor.getValue(),"l1\nl2\nl3\nl4\nl1\nl1\nl1\nl2\nl2\nl2\nl3\nl3\nl3\nl4\nl4\nl4");
        testSelection(editor, [[0,2],[0,1,0,0],[1,0,1,1],[2,0,2,1],[3,0,3,1]]);
    },

    "test multiselect fromJSON/toJSON": function() {
        var doc = new EditSession(["l1", "l2"]);
        editor = new Editor(new MockRenderer(), doc);
        var selection = editor.selection;
        
        var before = selection.toJSON();
        
        var range1 = new Range(0,2,0,2);
        var range2 = new Range(1,2,1,2);
        selection.fromOrientedRange(range1);
        selection.addRange(range2);
        
        var after = selection.toJSON();
        
        selection.fromJSON(before);
        assert.ok(!selection.isEqual(after));
        assert.ok(selection.isEqual(before));
        
        selection.fromJSON(after);
        assert.ok(!selection.isEqual(before));
        assert.ok(selection.isEqual(after));
    },
    
    "test multiselect align": function() {
        var doc = new EditSession(["l1", "l2", "l3"]);
        doc.setUndoManager(new UndoManager());
        editor = new Editor(new MockRenderer(), doc);
        var selection = editor.selection;
        selection.addRange(new Range(1,0,1,0))
        selection.addRange(new Range(2,2,2,2))
        editor.execCommand("alignCursors");
        assert.equal('  l1\n  l2\nl3', editor.getValue());
        doc.markUndoGroup();
        editor.execCommand("undo");
        assert.equal('l1\nl2\nl3', editor.getValue());
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
