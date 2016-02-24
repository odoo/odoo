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

var JavaScriptMode = require("../javascript").Mode;
var EditSession = require("../../edit_session").EditSession;
var assert = require("../../test/assertions");

module.exports = {

    "test: fold comments": function() {
        var session = new EditSession([
            '/*',
            'stuff',
            '*/'
        ]);
        
        var mode = new JavaScriptMode();
        session.setFoldStyle("markbeginend");
        session.setMode(mode);
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "");
        assert.equal(session.getFoldWidget(2), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 2, 2, 0);
        assert.range(session.getFoldWidgetRange(2), 0, 2, 2, 0);
    },
    
    "test: fold doc style comments": function() {
        var session = new EditSession([
            '/**',
            ' * stuff',
            ' * *** */'
        ]);
        
        var mode = new JavaScriptMode();
        session.setFoldStyle("markbeginend");
        session.setMode(mode);
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "");
        assert.equal(session.getFoldWidget(2), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 2, 2, 7);
        assert.range(session.getFoldWidgetRange(2), 0, 2, 2, 7);
    },
    
    "test: fold sections": function() {
        var session = new EditSession([
            '/* section0 */',
            '{',
            '    /* section1 */',
            '    stuff',
            '       ',
            '    /* section2 */',
            '       ',
            '    stuff',
            '       ',
            '     }',
            'foo'
        ]);
        
        var mode = new JavaScriptMode();
        session.setFoldStyle("markbegin");
        session.setMode(mode);
        
        assert.range(session.getFoldWidgetRange(0, true), 0, 14, 10, 3);
        assert.range(session.getFoldWidgetRange(2, true), 2, 18, 3, 9);
        assert.range(session.getFoldWidgetRange(5, true), 5, 18, 7, 9);
    }
};

});

if (typeof module !== "undefined" && module === require.main)
    require("asyncjs").test.testcase(module.exports).exec();
