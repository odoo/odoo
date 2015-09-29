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
var Editor = require("./editor").Editor;
var MockRenderer = require("./test/mockrenderer").MockRenderer;
var MultiSelect = require("./multi_select").MultiSelect;

var snippetManager = require("./snippets").snippetManager;
var assert = require("./test/assertions");

module.exports = {
    setUp : function(next) {
        this.editor = new Editor(new MockRenderer());
        next();
    },
    
    "test: textmate style format strings" : function() {
        var fmt = snippetManager.tmStrFormat;
        snippetManager.tmStrFormat("hello", {
            guard: "(..)(.)(.)",
            flag:"g",
            fmt: "a\\UO\\l$1\\E$2"
        }) == "aOHElo";
    },
    "test: parse snipmate file" : function() {
        var expected = [{
            name: "a",
            guard: "(?:(=)|(:))?s*)",
            trigger: "\\(?f",
            endTrigger: "\\)",
			endGuard: "",
            content: "{$0}\n"
         }, {
            tabTrigger: "f",
            name: "f function",
            content: "function"
        }];
		
		
		
        var parsed = snippetManager.parseSnippetFile(
            "name a\nregex /(?:(=)|(:))?\s*)/\\(?f/\\)/\n\t{$0}" +
            "\n\t\n\n#function\nsnippet f function\n\tfunction"
        );

        assert.equal(JSON.stringify(expected, null, 4), JSON.stringify(parsed, null, 4))
    },
    "test: parse snippet": function() {
        var content = "-\\$$2a${1:x${$2:y$3\\}\\n\\}$TM_SELECTION}";
        var tokens = snippetManager.tokenizeTmSnippet(content);
        assert.equal(tokens.length, 15);
        assert.equal(tokens[4], tokens[14]);
        assert.equal(tokens[2].tabstopId, 2);

        var content = "\\}${var/as\\/d/\\ul\\//g:s}"
        var tokens = snippetManager.tokenizeTmSnippet(content);
        assert.equal(tokens.length, 4);
        assert.equal(tokens[1], tokens[3]);
        assert.equal(tokens[2], "s");
        assert.equal(tokens[1].text, "var");
        assert.equal(tokens[1].fmt, "\\ul\\/");
        assert.equal(tokens[1].guard, "as\\/d");
        assert.equal(tokens[1].flag, "g");
    },
    "test: expand snippet with nested tabstops": function() {
        var content = "-${1}-${1:1}--${2:2 ${3} 2}-${3:3 $1 3}-${4:4 $2 4}";
        this.editor.setValue("");
        snippetManager.insertSnippet(this.editor, content);
        assert.equal(this.editor.getValue(), "-1-1--2 3 1 3 2-3 1 3-4 2 3 1 3 2 4");
        
        assert.equal(this.editor.getSelectedText(), "1\n1\n1\n1\n1");
        this.editor.tabstopManager.tabNext();
        assert.equal(this.editor.getSelectedText(), "2 3 1 3 2\n2 3 1 3 2");
        this.editor.tabstopManager.tabNext();
        assert.equal(this.editor.getSelectedText(), "3 1 3\n3 1 3\n3 1 3");
        this.editor.tabstopManager.tabNext();
        assert.equal(this.editor.getSelectedText(), "4 2 3 1 3 2 4");
        this.editor.tabstopManager.tabNext();
        assert.equal(this.editor.getSelectedText(), "");
        
        this.editor.setValue("");
        snippetManager.insertSnippet(this.editor, "-${1:a$2}-${2:b$1}");
        assert.equal(this.editor.getValue(), "-ab-ba");
        
        assert.equal(this.editor.getSelectedText(), "ab\na");
        this.editor.tabstopManager.tabNext();
        assert.equal(this.editor.getSelectedText(), "b\nba");
        this.editor.tabstopManager.tabNext();
        assert.equal(this.editor.getSelectedText(), "");
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
