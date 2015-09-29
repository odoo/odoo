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
var Text = require("./mode/text").Mode;
var JavaScriptMode = require("./mode/javascript").Mode;
var CssMode = require("./mode/css").Mode;
var HtmlMode = require("./mode/html").Mode;
var MockRenderer = require("./test/mockrenderer").MockRenderer;
var assert = require("./test/assertions");

module.exports = {

    setUp : function(next) {
        this.session1 = new EditSession(["abc", "def"]);
        this.session2 = new EditSession(["ghi", "jkl"]);
        
        
        this.editor = new Editor(new MockRenderer());
        next();
    },

    "test: change document" : function() {
        this.editor.setSession(this.session1);
        assert.equal(this.editor.getSession(), this.session1);

        this.editor.setSession(this.session2);
        assert.equal(this.editor.getSession(), this.session2);
    },

    "test: only changes to the new document should have effect" : function() {
        var called = false;
        this.editor.onDocumentChange = function() {
            called = true;
        };

        this.editor.setSession(this.session1);
        this.editor.setSession(this.session2);

        this.session1.duplicateLines(0, 0);
        assert.notOk(called);

        this.session2.duplicateLines(0, 0);
        assert.ok(called);
    },

    "test: should use cursor of new document" : function() {
        this.session1.getSelection().moveCursorTo(0, 1);
        this.session2.getSelection().moveCursorTo(1, 0);

        this.editor.setSession(this.session1);
        assert.position(this.editor.getCursorPosition(), 0, 1);

        this.editor.setSession(this.session2);
        assert.position(this.editor.getCursorPosition(), 1, 0);
    },

    "test: only changing the cursor of the new doc should not have an effect" : function() {
        this.editor.onCursorChange = function() {
            called = true;
        };

        this.editor.setSession(this.session1);
        this.editor.setSession(this.session2);
        assert.position(this.editor.getCursorPosition(), 0, 0);

        var called = false;
        this.session1.getSelection().moveCursorTo(0, 1);
        assert.position(this.editor.getCursorPosition(), 0, 0);
        assert.notOk(called);

        this.session2.getSelection().moveCursorTo(1, 1);
        assert.position(this.editor.getCursorPosition(), 1, 1);
        assert.ok(called);
    },

    "test: should use selection of new document" : function() {
        this.session1.getSelection().selectTo(0, 1);
        this.session2.getSelection().selectTo(1, 0);

        this.editor.setSession(this.session1);
        assert.position(this.editor.getSelection().getSelectionLead(), 0, 1);

        this.editor.setSession(this.session2);
        assert.position(this.editor.getSelection().getSelectionLead(), 1, 0);
    },

    "test: only changing the selection of the new doc should not have an effect" : function() {
        this.editor.onSelectionChange = function() {
            called = true;
        };

        this.editor.setSession(this.session1);
        this.editor.setSession(this.session2);
        assert.position(this.editor.getSelection().getSelectionLead(), 0, 0);

        var called = false;
        this.session1.getSelection().selectTo(0, 1);
        assert.position(this.editor.getSelection().getSelectionLead(), 0, 0);
        assert.notOk(called);

        this.session2.getSelection().selectTo(1, 1);
        assert.position(this.editor.getSelection().getSelectionLead(), 1, 1);
        assert.ok(called);
    },

    "test: should use mode of new document" : function() {
        this.editor.onChangeMode = function() {
            called = true;
        };
        this.editor.setSession(this.session1);
        this.editor.setSession(this.session2);

        var called = false;
        this.session1.setMode(new Text());
        assert.notOk(called);

        this.session2.setMode(new JavaScriptMode());
        assert.ok(called);
    },
    
    "test: should use stop worker of old document" : function(next) {
        var self = this;
        
        // 1. Open an editor and set the session to CssMode
        self.editor.setSession(self.session1);
        self.session1.setMode(new CssMode());
        
        // 2. Add a line or two of valid CSS.
        self.session1.setValue("DIV { color: red; }");
        
        // 3. Clear the session value.
        self.session1.setValue("");
        
        // 4. Set the session to HtmlMode
        self.session1.setMode(new HtmlMode());

        // 5. Try to type valid HTML
        self.session1.insert({row: 0, column: 0}, "<html></html>");
        
        setTimeout(function() {
            assert.equal(Object.keys(self.session1.getAnnotations()).length, 0);
            next();
        }, 600);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
