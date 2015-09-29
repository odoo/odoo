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
var JavaScriptMode = require("./mode/javascript").Mode;
var Range = require("./range").Range;
var assert = require("./test/assertions");

function forceTokenize(session){
    for (var i = 0, l = session.getLength(); i < l; i++)
        session.getTokens(i)
}

function testStates(session, states) {
    for (var i = 0, l = session.getLength(); i < l; i++)
        assert.equal(session.bgTokenizer.states[i], states[i])
    assert.ok(l == states.length)
}

module.exports = {

    "test background tokenizer update on session change" : function() {
        var doc = new EditSession([
            "/*",
            "*/",
            "var juhu"
        ]);
        doc.setMode("./mode/javascript")  
        
        forceTokenize(doc)
        testStates(doc, ["comment_regex_allowed", "start", "no_regex"])
        
        doc.remove(new Range(0,2,1,2))
        testStates(doc, [null, "no_regex"])
        
        forceTokenize(doc)
        testStates(doc, ["comment_regex_allowed", "comment_regex_allowed"])
        
        doc.insert({row:0, column:2}, "\n*/")
        testStates(doc, [undefined, undefined, "comment_regex_allowed"])
        
        forceTokenize(doc)
        testStates(doc, ["comment_regex_allowed", "start", "no_regex"])
    },
    "test background tokenizer sends update event" : function() {
        var doc = new EditSession([
            "/*",
            "var",
            "juhu",
            "*/"
        ]);
        doc.setMode("./mode/javascript");
        
        var updateEvent = null;
        doc.bgTokenizer.on("update", function(e) {
            updateEvent = e.data;
        });
        function checkEvent(first, last) {
            assert.ok(!updateEvent, "unneccessary update event");
            doc.bgTokenizer.running = 1;
            doc.bgTokenizer.$worker();
            assert.ok(updateEvent);
            assert.equal([first, last] + "", 
                [updateEvent.first, updateEvent.last] + "")
            updateEvent = null;
        }
        
        forceTokenize(doc);
        var comment = "comment_regex_allowed";
        testStates(doc, [comment, comment, comment, "start"]);
        
        doc.remove(new Range(0,0,0,2));
        testStates(doc, [comment, comment, comment, "start"]);
        
        checkEvent(0, 3);
        testStates(doc, ["start", "no_regex", "no_regex", "regex"]);
        
        // insert /* and and press down several times quickly
        doc.insert({row:0, column:0}, "/*");
        doc.getTokens(0);
        doc.getTokens(1);
        doc.getTokens(2);
        checkEvent(0, 3);
        
        forceTokenize(doc);
        testStates(doc, [comment, comment, comment, "start"]);
    }
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
