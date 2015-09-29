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

if (typeof process !== "undefined")
    require("amd-loader");

define(function(require, exports, module) {
"use strict";

var CoffeeMode = require("../coffee").Mode;
var EditSession = require("../../edit_session").EditSession;
var assert = require("../../test/assertions");
function testFoldWidgets(array) {
    var session = array.filter(function(_, i){return i % 2 == 1});
    session = new EditSession(session);
    var mode = new CoffeeMode();
    session.setFoldStyle("markbeginend");
    session.setMode(mode);

    var widgets = array.filter(function(_, i){return i % 2 == 0});
    widgets.forEach(function(w, i){
        session.foldWidgets[i] = session.getFoldWidget(i);
    })
    widgets.forEach(function(w, i){
        w = w.split(",");
        var type = w[0] == ">" ? "start" : w[0] == "<" ? "end" : "";
        assert.equal(session.foldWidgets[i], type);
        if (!type)
            return;
        var range = session.getFoldWidgetRange(i);
        if (!w[1]) {
            assert.equal(range, null);
            return;
        }
        assert.equal(range.start.row, i);
        assert.equal(range.end.row - range.start.row, parseInt(w[1]));
        testColumn(w[2], range.start);
        testColumn(w[3], range.end);
    });

    function testColumn(w, pos) {
        if (!w)
            return;
        if (w == "l")
            w = session.getLine(pos.row).length;
        else
            w = parseInt(w);
        assert.equal(pos.column, w);
    }
}
module.exports = {
    "test: coffee script indentation based folding": function() {
       testFoldWidgets([
            '>,1,l,l',         ' ## indented comment',
            '',                '  # ',
            '',                '',
            '>,1,l,l',         ' # plain comment',
            '',                ' # ',
            '>,2',             ' function (x)=>',
            '',                '  ',
            '',                '  x++',
            '',                '  ',
            '',                '  ',
            '>,2',             ' bar = ',
            '',                '   foo: 1',
            '',                '   baz: lighter'
        ]);
    }
};

});

if (typeof module !== "undefined" && module === require.main)
    require("asyncjs").test.testcase(module.exports).exec();
