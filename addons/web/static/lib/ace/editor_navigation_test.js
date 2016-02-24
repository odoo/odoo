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

module.exports = {
    createEditSession : function(rows, cols) {
        var line = new Array(cols + 1).join("a");
        var text = new Array(rows).join(line + "\n") + line;
        return new EditSession(text);
    },

    "test: navigate to end of file should scroll the last line into view" : function() {
        var doc = this.createEditSession(200, 10);
        var editor = new Editor(new MockRenderer(), doc);

        editor.navigateFileEnd();
        var cursor = editor.getCursorPosition();

        assert.ok(editor.getFirstVisibleRow() <= cursor.row);
        assert.ok(editor.getLastVisibleRow() >= cursor.row);
    },

    "test: navigate to start of file should scroll the first row into view" : function() {
        var doc = this.createEditSession(200, 10);
        var editor = new Editor(new MockRenderer(), doc);

        editor.moveCursorTo(editor.getLastVisibleRow() + 20);
        editor.navigateFileStart();

        assert.equal(editor.getFirstVisibleRow(), 0);
    },

    "test: goto hidden line should scroll the line into the middle of the viewport" : function() {
        var editor = new Editor(new MockRenderer(), this.createEditSession(200, 5));

        editor.navigateTo(0, 0);
        editor.gotoLine(101);
        assert.position(editor.getCursorPosition(), 100, 0);
        assert.equal(editor.getFirstVisibleRow(), 89);

        editor.navigateTo(100, 0);
        editor.gotoLine(11);
        assert.position(editor.getCursorPosition(), 10, 0);
        assert.equal(editor.getFirstVisibleRow(), 0);

        editor.navigateTo(100, 0);
        editor.gotoLine(6);
        assert.position(editor.getCursorPosition(), 5, 0);
        assert.equal(0, editor.getFirstVisibleRow(), 0);

        editor.navigateTo(100, 0);
        editor.gotoLine(1);
        assert.position(editor.getCursorPosition(), 0, 0);
        assert.equal(editor.getFirstVisibleRow(), 0);

        editor.navigateTo(0, 0);
        editor.gotoLine(191);
        assert.position(editor.getCursorPosition(), 190, 0);
        assert.equal(editor.getFirstVisibleRow(), 179);

        editor.navigateTo(0, 0);
        editor.gotoLine(196);
        assert.position(editor.getCursorPosition(), 195, 0);
        assert.equal(editor.getFirstVisibleRow(), 180);
    },

    "test: goto visible line should only move the cursor and not scroll": function() {
        var editor = new Editor(new MockRenderer(), this.createEditSession(200, 5));

        editor.navigateTo(0, 0);
        editor.gotoLine(12);
        assert.position(editor.getCursorPosition(), 11, 0);
        assert.equal(editor.getFirstVisibleRow(), 0);

        editor.navigateTo(30, 0);
        editor.gotoLine(33);
        assert.position(editor.getCursorPosition(), 32, 0);
        assert.equal(editor.getFirstVisibleRow(), 30);
    },

    "test: navigate from the end of a long line down to a short line and back should maintain the curser column": function() {
        var editor = new Editor(new MockRenderer(), new EditSession(["123456", "1"]));

        editor.navigateTo(0, 6);
        assert.position(editor.getCursorPosition(), 0, 6);

        editor.navigateDown();
        assert.position(editor.getCursorPosition(), 1, 1);

        editor.navigateUp();
        assert.position(editor.getCursorPosition(), 0, 6);
    },

    "test: reset desired column on navigate left or right": function() {
        var editor = new Editor(new MockRenderer(), new EditSession(["123456", "12"]));

        editor.navigateTo(0, 6);
        assert.position(editor.getCursorPosition(), 0, 6);

        editor.navigateDown();
        assert.position(editor.getCursorPosition(), 1, 2);

        editor.navigateLeft();
        assert.position(editor.getCursorPosition(), 1, 1);

        editor.navigateUp();
        assert.position(editor.getCursorPosition(), 0, 1);
    },
    
    "test: typing text should update the desired column": function() {
        var editor = new Editor(new MockRenderer(), new EditSession(["1234", "1234567890"]));

        editor.navigateTo(0, 3);
        editor.insert("juhu");
        
        editor.navigateDown();
        assert.position(editor.getCursorPosition(), 1, 7);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
