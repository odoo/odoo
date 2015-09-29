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

var Editor = require("../editor").Editor;
var MockRenderer = require("../test/mockrenderer").MockRenderer;
var assert = require("../test/assertions");
var MouseEvent = function(type, opts){
    var e = document.createEvent("MouseEvents");
    e.initMouseEvent("mouse" + type,
        true, true, window,
        opts.detail,
        opts.x, opts.y, opts.x, opts.y,
        opts.ctrl, opts.alt, opts.shift, opts.meta,
        opts.button || 0, opts.relatedTarget);
    return e;
};

module.exports = {

    setUp : function(next) {
        this.editor = new Editor(new MockRenderer());
        this.editor.setValue("Juhu kinners!")
        next();
    },

    "test: double tap. issue #956" : function() {
        // mouse up fired immediately after mouse down
        var target = this.editor.renderer.getMouseEventTarget();
        target.dispatchEvent(MouseEvent("down", {x: 1, y: 1}));
        target.dispatchEvent(MouseEvent("up", {x: 1, y: 1}));
        target.dispatchEvent(MouseEvent("down", {x: 1, y: 1, detail: 2}));
        target.dispatchEvent(MouseEvent("up", {x: 1, y: 1, detail: 2}));
        
        assert.equal(this.editor.getSelectedText(), "Juhu");
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
