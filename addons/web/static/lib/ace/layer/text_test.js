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
    require("../test/mockdom");
}

define(function(require, exports, module) {
"use strict";

var assert = require("../test/assertions");
var EditSession = require("../edit_session").EditSession;
var TextLayer = require("./text").Text;
var JavaScriptMode = require("../mode/javascript").Mode;

module.exports = {

    setUp: function(next) {
        this.session = new EditSession("");
        this.session.setMode(new JavaScriptMode());
        this.textLayer = new TextLayer(document.createElement("div"));
        this.textLayer.setSession(this.session);
        this.textLayer.config = {
            characterWidth: 10,
            lineHeight: 20
        };
        next()
    },

    "test: render line with hard tabs should render the same as lines with soft tabs" : function() {
        this.session.setValue("a\ta\ta\t\na   a   a   \n");
        this.textLayer.$computeTabString();
        
        // row with hard tabs
        var stringBuilder = [];
        this.textLayer.$renderLine(stringBuilder, 0);
        
        // row with soft tabs
        var stringBuilder2 = [];
        this.textLayer.$renderLine(stringBuilder2, 1);
        assert.equal(stringBuilder.join(""), stringBuilder2.join(""));
    },
    
    "test rendering width of ideographic space (U+3000)" : function() {
        this.session.setValue("\u3000");
        
        var stringBuilder = [];
        this.textLayer.$renderLine(stringBuilder, 0, true);
        assert.equal(stringBuilder.join(""), "<span class='ace_cjk' style='width:20px'></span>");

        this.textLayer.setShowInvisibles(true);
        var stringBuilder = [];
        this.textLayer.$renderLine(stringBuilder, 0, true);
        assert.equal(
            stringBuilder.join(""),
            "<span class='ace_cjk ace_invisible ace_invisible_space' style='width:20px'>" + this.textLayer.SPACE_CHAR + "</span>"
            + "<span class='ace_invisible ace_invisible_eol'>\xB6</span>"
        );
    },

    "test rendering of indent guides" : function() {
        var textLayer = this.textLayer
        var EOL = "<span class='ace_invisible ace_invisible_eol'>" + textLayer.EOL_CHAR + "</span>";
        var SPACE = function(i) {return Array(i+1).join(" ")}
        var DOT = function(i) {return Array(i+1).join(textLayer.SPACE_CHAR)}
        var TAB = function(i) {return Array(i+1).join(textLayer.TAB_CHAR)}
        function testRender(results) {
            for (var i = results.length; i--; ) {
                var stringBuilder = [];
                textLayer.$renderLine(stringBuilder, i, true);
                assert.equal(stringBuilder.join(""), results[i]);
            }
        }
        
        this.session.setValue("      \n\t\tf\n   ");
        testRender([
            "<span class='ace_indent-guide'>" + SPACE(4) + "</span>" + SPACE(2),
            "<span class='ace_indent-guide'>" + SPACE(4) + "</span>" + SPACE(4) + "<span class='ace_identifier'>f</span>",
            SPACE(3)
        ]);
        this.textLayer.setShowInvisibles(true);
        testRender([
            "<span class='ace_indent-guide ace_invisible ace_invisible_space'>" + DOT(4) + "</span><span class='ace_invisible ace_invisible_space'>" + DOT(2) + "</span>" + EOL,
            "<span class='ace_indent-guide ace_invisible ace_invisible_tab'>" + TAB(4) + "</span><span class='ace_invisible ace_invisible_tab'>" + TAB(4) + "</span><span class='ace_identifier'>f</span>" + EOL,
        ]);
        this.textLayer.setDisplayIndentGuides(false);
        testRender([
            "<span class='ace_invisible ace_invisible_space'>" + DOT(6) + "</span>" + EOL,
            "<span class='ace_invisible ace_invisible_tab'>" + TAB(4) + "</span><span class='ace_invisible ace_invisible_tab'>" + TAB(4) + "</span><span class='ace_identifier'>f</span>" + EOL
        ]);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
