/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2014, Ajax.org B.V.
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

define(function(require, exports, module) {

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
var stringEscape =  "\\\\(x[0-9A-Fa-f]{2}|[0-7]{3}|[\\\\abfnrtv'\"]|U[0-9A-Fa-f]{8}|u[0-9A-Fa-f]{4})";

var GherkinHighlightRules = function() {
    var languages = [{
        name: "en",
        labels: "Feature|Background|Scenario(?: Outline)?|Examples",
        keywords: "Given|When|Then|And|But"
    }
    /* TODO find a way to enable this when first line in the file is # language: pl
    , {
        name: "pl",
        labels: "Właściwość|Funkcja|Aspekt|Potrzeba biznesowa|Założenia|Scenariusz|Szablon scenariusza|Przykłady",
        keywords: "Mając|Zakładając(?:, że)?|Jeżeli|Jeśli|Gdy|Kiedy|Wtedy|Oraz|I|Ale"
    }
    */];
    
    var labels = languages.map(function(l) {
        return l.labels;
    }).join("|");
    var keywords = languages.map(function(l) {
        return l.keywords;
    }).join("|");
    
    // need to include constant ints
    this.$rules = {
        start : [{
            token: 'constant.numeric',
            regex: "(?:(?:[1-9]\\d*)|(?:0))"
        }, {
            token : "comment",
            regex : "#.*$"
        }, {
            token : "keyword",
            regex : "(?:" + labels + "):|(?:" + keywords + ")\\b",
        }, {
            token : "keyword",
            regex : "\\*",
        }, {
            token : "string",           // multi line """ string start
            regex : '"{3}',
            next : "qqstring3"
        }, {
            token : "string",           // " string
            regex : '"',
            next : "qqstring"
        }, {
            token : "text",
            regex : "^\\s*(?=@[\\w])",
            next : [{
                token : "text",
                regex : "\\s+",
            }, {
                token : "variable.parameter",
                regex : "@[\\w]+"
            }, {
                token : "empty",
                regex : "",
                next : "start"
            }]
        }, {
            token : "comment",
            regex : "<[^>]+>"
        }, {
            token : "comment",
            regex : "\\|(?=.)",
            next : "table-item"
        }, {
            token : "comment",
            regex : "\\|$",
            next : "start"
        }],
        "qqstring3" : [ {
            token : "constant.language.escape",
            regex : stringEscape
        }, {
            token : "string", // multi line """ string end
            regex : '"{3}',
            next : "start"
        }, {
            defaultToken : "string"
        }],
        "qqstring" : [{
            token : "constant.language.escape",
            regex : stringEscape
        }, {
            token : "string",
            regex : "\\\\$",
            next  : "qqstring"
        }, {
            token : "string",
            regex : '"|$',
            next  : "start"
        }, {
            defaultToken: "string"
        }],
        "table-item" : [{
            token : "comment",
            regex : /$/,
            next : "start"
        }, {
            token : "comment",
            regex : /\|/
        }, {
            token : "string",
            regex : /\\./
        }, {
            defaultToken : "string"
        }]
    };
    this.normalizeRules();
}

oop.inherits(GherkinHighlightRules, TextHighlightRules);

exports.GherkinHighlightRules = GherkinHighlightRules;
});