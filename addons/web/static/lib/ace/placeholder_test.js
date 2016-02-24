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
var JavaScriptMode = require("./mode/javascript").Mode;
var PlaceHolder = require("./placeholder").PlaceHolder;
var UndoManager = require("./undomanager").UndoManager;
require("./multi_select")

module.exports = {

   "test: simple at the end appending of text" : function() {
        var session = new EditSession("var a = 10;\nconsole.log(a, a);", new JavaScriptMode());
        var editor = new Editor(new MockRenderer(), session);
        
        new PlaceHolder(session, 1, {row: 0, column: 4}, [{row: 1, column: 12}, {row: 1, column: 15}]);
        
        editor.moveCursorTo(0, 5);
        editor.insert('b');
        assert.equal(session.doc.getValue(), "var ab = 10;\nconsole.log(ab, ab);");
        editor.insert('cd');
        assert.equal(session.doc.getValue(), "var abcd = 10;\nconsole.log(abcd, abcd);");
        editor.remove('left');
        editor.remove('left');
        editor.remove('left');
        assert.equal(session.doc.getValue(), "var a = 10;\nconsole.log(a, a);");
    },

    "test: inserting text outside placeholder" : function() {
        var session = new EditSession("var a = 10;\nconsole.log(a, a);\n", new JavaScriptMode());
        var editor = new Editor(new MockRenderer(), session);
        
        new PlaceHolder(session, 1, {row: 0, column: 4}, [{row: 1, column: 12}, {row: 1, column: 15}]);
        
        editor.moveCursorTo(2, 0);
        editor.insert('b');
        assert.equal(session.doc.getValue(), "var a = 10;\nconsole.log(a, a);\nb");
    },
    
   "test: insertion at the beginning" : function(next) {
        var session = new EditSession("var a = 10;\nconsole.log(a, a);", new JavaScriptMode());
        var editor = new Editor(new MockRenderer(), session);
        
        var p = new PlaceHolder(session, 1, {row: 0, column: 4}, [{row: 1, column: 12}, {row: 1, column: 15}]);
        
        editor.moveCursorTo(0, 4);
        editor.insert('$');
        assert.equal(session.doc.getValue(), "var $a = 10;\nconsole.log($a, $a);");
        editor.moveCursorTo(0, 4);
        // Have to put this in a setTimeout because the anchor is only fixed later.
        setTimeout(function() {
            editor.insert('v');
            assert.equal(session.doc.getValue(), "var v$a = 10;\nconsole.log(v$a, v$a);");
            next();
        }, 20);
    },

   "test: detaching placeholder" : function() {
        var session = new EditSession("var a = 10;\nconsole.log(a, a);", new JavaScriptMode());
        var editor = new Editor(new MockRenderer(), session);
        
        var p = new PlaceHolder(session, 1, {row: 0, column: 4}, [{row: 1, column: 12}, {row: 1, column: 15}]);
        
        editor.moveCursorTo(0, 5);
        editor.insert('b');
        assert.equal(session.doc.getValue(), "var ab = 10;\nconsole.log(ab, ab);");
        p.detach();
        editor.insert('cd');
        assert.equal(session.doc.getValue(), "var abcd = 10;\nconsole.log(ab, ab);");
    },

   "test: events" : function() {
        var session = new EditSession("var a = 10;\nconsole.log(a, a);", new JavaScriptMode());
        var editor = new Editor(new MockRenderer(), session);
        
        var p = new PlaceHolder(session, 1, {row: 0, column: 4}, [{row: 1, column: 12}, {row: 1, column: 15}]);
        var entered = false;
        var left = false;
        p.on("cursorEnter", function() {
            entered = true;
        });
        p.on("cursorLeave", function() {
            left = true;
        });
        
        editor.moveCursorTo(0, 0);
        editor.moveCursorTo(0, 4);
        p.onCursorChange(); // Have to do this by hand because moveCursorTo doesn't trigger the event
        assert.ok(entered);
        editor.moveCursorTo(1, 0);
        p.onCursorChange(); // Have to do this by hand because moveCursorTo doesn't trigger the event
        assert.ok(left);
    },
    
    "test: cancel": function(next) {
        var session = new EditSession("var a = 10;\nconsole.log(a, a);", new JavaScriptMode());
        session.setUndoManager(new UndoManager());
        var editor = new Editor(new MockRenderer(), session);
        var p = new PlaceHolder(session, 1, {row: 0, column: 4}, [{row: 1, column: 12}, {row: 1, column: 15}]);
        
        editor.moveCursorTo(0, 5);
        editor.insert('b');
        editor.insert('cd');
        editor.remove('left');
        assert.equal(session.doc.getValue(), "var abc = 10;\nconsole.log(abc, abc);");
        // Wait a little for the changes to enter the undo stack
        setTimeout(function() {
            p.cancel();
            assert.equal(session.doc.getValue(), "var a = 10;\nconsole.log(a, a);");
            next();
        }, 80);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
