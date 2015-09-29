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
    require("../../test/mockdom");
}

define(function(require, exports, module) {
"use strict";

require("../../multi_select");
var assert = require("../../test/assertions");
var Range = require("../../range").Range;
var Editor = require("../../editor").Editor;
var EditSession = require("../../edit_session").EditSession;
var MockRenderer = require("../../test/mockrenderer").MockRenderer;
var JavaScriptMode = require("../javascript").Mode;
var XMLMode = require("../xml").Mode;
var editor;
var exec = function(name, times, args) {
    do {
        editor.commands.exec(name, editor, args);
    } while(times --> 1);
};
var testRanges = function(str) {
    assert.equal(editor.selection.getAllRanges() + "", str + "");
};

module.exports = {
    "test: cstyle": function() {
        function testValue(line) {
            assert.equal(editor.getValue(), Array(4).join(line + "\n"));
        }
        function testSelection(line, col, inc) {
            editor.selection.rangeList.ranges.forEach(function(r) {
                assert.range(r, line, col, line, col);
                line += (inc || 1);
            });
        }
        var doc = new EditSession([
            "",
            "",
            "",
            ""
        ], new JavaScriptMode());
        editor = new Editor(new MockRenderer(), doc);
        editor.setOption("behavioursEnabled", true);

        editor.navigateFileStart();
        exec("addCursorBelow", 2);

        exec("insertstring", 1, "if ");
        
        // pairing ( 
        exec("insertstring", 1, "(");
        testValue("if ()");
        testSelection(0, 4);
        exec("insertstring", 1, ")");
        testValue("if ()");
        testSelection(0, 5);
        
        // pairing [ 
        exec("gotoleft", 1);
        exec("insertstring", 1, "[");
        testValue("if ([])");
        testSelection(0, 5);
        
        exec("insertstring", 1, "]");
        testValue("if ([])");
        testSelection(0, 6);
        
        // test deletion
        exec("gotoleft", 1);
        exec("backspace", 1);
        testValue("if ()");
        testSelection(0, 4);

        exec("gotolineend", 1);
        exec("insertstring", 1, "{");
        testValue("if (){}");
        testSelection(0, 6);
        
        exec("insertstring", 1, "}");
        testValue("if (){}");
        testSelection(0, 7);
        
        exec("gotolinestart", 1);
        exec("insertstring", 1, "(");
        testValue("(if (){}");
        exec("backspace", 1);
        
        editor.setValue("");
        exec("insertstring", 1, "{");
        assert.equal(editor.getValue(), "{");
        exec("insertstring", 1, "\n");
        assert.equal(editor.getValue(), "{\n    \n}");
        
        editor.setValue("");
        exec("insertstring", 1, "(");
        exec("insertstring", 1, '"');
        exec("insertstring", 1, '"');
        assert.equal(editor.getValue(), '("")');
        exec("backspace", 1);
        exec("insertstring", 1, '"');
        assert.equal(editor.getValue(), '("")');
        
        editor.setValue("('foo')", 1);
        exec("gotoleft", 1);
        exec("selectleft", 1);
        exec("selectMoreBefore", 1);
        exec("insertstring", 1, "'");
        assert.equal(editor.getValue(), "('foo')");
        exec("selectleft", 1);
        exec("insertstring", 1, '"');
        assert.equal(editor.getValue(), '("foo")');
        exec("selectleft", 1);
        exec("insertstring", 1, '"');
        assert.equal(editor.getValue(), '("foo")');
        
        editor.setValue("", 1);
        exec("selectleft", 1);
        exec("insertstring", 1, '"');
        assert.equal(editor.getValue(), '""');
        exec("insertstring", 1, '\\');
        exec("insertstring", 1, 'n');
        exec("insertstring", 1, '"');
        assert.equal(editor.getValue(), '"\\n"');
        
    },
    "test: xml": function() {
        editor = new Editor(new MockRenderer());
        editor.setValue(["<OuterTag>",
            "    <SelfClosingTag />"
        ].join("\n"));
        editor.session.setMode(new XMLMode);
        exec("gotolinedown", 1);
        exec("gotolineend", 1);
        exec("insertstring", 1, '\n');
        assert.equal(editor.session.getLine(2), "    ");
        exec("gotolineup", 1);
        exec("gotolineend", 1);
        exec("insertstring", 1, '\n');
        assert.equal(editor.session.getLine(2), "    ");
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec();
}
