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

var Tokenizer = require("./tokenizer").Tokenizer;
var assert = require("./test/assertions");

module.exports = {
    "test: createSplitterRegexp" : function() {
        var t = new Tokenizer({});
        var re = t.createSplitterRegexp("(a)(b)(?=[x)(])");
        assert.equal(re.source, "(a)(b)");
        var re = t.createSplitterRegexp("xc(?=([x)(]))");
        assert.equal(re.source, "xc");
        var re = t.createSplitterRegexp("(xc(?=([x)(])))");
        assert.equal(re.source, "(xc)");
        var re = t.createSplitterRegexp("(?=r)[(?=)](?=([x)(]))");
        assert.equal(re.source, "(?=r)[(?=)]");
        var re = t.createSplitterRegexp("(?=r)[(?=)](\\?=t)");
        assert.equal(re.source, "(?=r)[(?=)](\\?=t)");
        var re = t.createSplitterRegexp("[(?=)](\\?=t)");
        assert.equal(re.source, "[(?=)](\\?=t)");
    },

    "test: removeCapturingGroups" : function() {
        var t = new Tokenizer({});
        var re = t.removeCapturingGroups("(ax(by))[()]");
        assert.equal(re, "(?:ax(?:by))[()]");
    },
    
    "test: broken highlight rules": function() {
        var t = new Tokenizer({
            start: [{ 
                token: 's',
                regex: '&&&|^^^' 
            }, {
                defaultToken: "def"
            }],
            state1: [{ 
                token: 'x',
                regex: /\b([\w]*)(\s*)((?::)?)/
            }]
        });
        var errorReports = 0;
        t.reportError = function() { errorReports++; };
        var tokens = t.getLineTokens("x|", "start");
        assert.deepEqual(tokens, {
            tokens: [{value: 'x|', type: 'overflow'}],
            state: 'start'
        });
        var tokens = t.getLineTokens("x|", "state1");
        assert.deepEqual(tokens, {
            tokens: [{value: 'x', type: 'x'}, {value: '|', type: 'overflow'}],
            state: 'start'
        });
        assert.equal(errorReports, 2);
    }, 
};

});

if (typeof module !== "undefined" && module === require.main) {
    require("asyncjs").test.testcase(module.exports).exec()
}
