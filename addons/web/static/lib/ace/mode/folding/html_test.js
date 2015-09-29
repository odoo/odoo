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

var HtmlMode = require("../html").Mode;
var EditSession = require("../../edit_session").EditSession;
var assert = require("../../test/assertions");

module.exports = {

    "test: fold mixed html and javascript": function() {
        var session = new EditSession([
            '<script type="text/javascript"> ',
            'function() foo {',
            '    var bar = 1;',
            '}',
            '</script>'
        ]);
        
        var mode = new HtmlMode();
        session.setMode(mode);
        session.setFoldStyle("markbeginend");
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "start");
        assert.equal(session.getFoldWidget(2), "");
        assert.equal(session.getFoldWidget(3), "end");
        assert.equal(session.getFoldWidget(4), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 31, 4, 0);
        assert.range(session.getFoldWidgetRange(4), 0, 31, 4, 0);
        
        assert.range(session.getFoldWidgetRange(1), 1, 16, 3, 0);
        assert.range(session.getFoldWidgetRange(3), 1, 16, 3, 0);
    },
    
    "test: fold mixed html and css": function() {
        var session = new EditSession([
            '<style type="text/css">',
            '    .text-layer {',
            '        font-family: Monaco, "Courier New", monospace;',
            '    }',
            '</style>'
        ]);
        
        var mode = new HtmlMode();
        session.setMode(mode);
        session.setFoldStyle("markbeginend");
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "start");
        assert.equal(session.getFoldWidget(2), "");
        assert.equal(session.getFoldWidget(3), "end");
        assert.equal(session.getFoldWidget(4), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 23, 4, 0);
        assert.range(session.getFoldWidgetRange(4), 0, 23, 4, 0);
        
        assert.range(session.getFoldWidgetRange(1), 1, 17, 3, 4);
        assert.range(session.getFoldWidgetRange(3), 1, 17, 3, 4);
    },
    
    "test: fold should skip self closing elements": function() {
        var session = new EditSession([
            '<body>',
            '<br />',
            '</body>'
        ]);
        
        var mode = new HtmlMode();
        session.setMode(mode);
        session.setFoldStyle("markbeginend");
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "");
        assert.equal(session.getFoldWidget(2), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 6, 2, 0);
        assert.range(session.getFoldWidgetRange(2), 0, 6, 2, 0);
    },
    
    "test: fold should skip void elements": function() {
        var session = new EditSession([
            '<body>',
            '<br>',
            '</body>'
        ]);
        
        var mode = new HtmlMode();
        session.setMode(mode);
        session.setFoldStyle("markbeginend");
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "");
        assert.equal(session.getFoldWidget(2), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 6, 2, 0);
        assert.range(session.getFoldWidgetRange(2), 0, 6, 2, 0);
    },
    
    "test: fold multiple unclosed elements": function() {
        var session = new EditSession([
            '<div>',
            '<p>',
            'juhu',
            '<p>',
            'kinners',
            '</div>'
        ]);
        
        var mode = new HtmlMode();
        session.setMode(mode);
        session.setFoldStyle("markbeginend");
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "start");
        assert.equal(session.getFoldWidget(2), "");
        assert.equal(session.getFoldWidget(3), "start");
        assert.equal(session.getFoldWidget(4), "");
        assert.equal(session.getFoldWidget(5), "end");
        
        assert.range(session.getFoldWidgetRange(0), 0, 5, 5, 0);
        assert.range(session.getFoldWidgetRange(5), 0, 5, 5, 0);
    },
    
    "test: fold multiple nested optional elements": function() {
        var session = new EditSession([
            '<p>',
            '<li>',
            '<p>juhu',
            '<p>',
            'kinners',
            '</li>'
        ]);
        
        var mode = new HtmlMode();
        session.setMode(mode);
        session.setFoldStyle("markbeginend");
        
        assert.equal(session.getFoldWidget(0), "start");
        assert.equal(session.getFoldWidget(1), "start");
        assert.equal(session.getFoldWidget(2), "start");
        assert.equal(session.getFoldWidget(3), "start");
        assert.equal(session.getFoldWidget(4), "");
        assert.equal(session.getFoldWidget(5), "end");
        
        assert.range(session.getFoldWidgetRange(1), 1, 4, 5, 0);
    }
};

});

if (typeof module !== "undefined" && module === require.main)
    require("asyncjs").test.testcase(module.exports).exec();
