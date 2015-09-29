/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2012, Ajax.org B.V.
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
var HtmlMode = require("./html").Mode;
var HtmlHighlightRules = require("./html_highlight_rules").HtmlHighlightRules;
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var DjangoHighlightRules = function(){
    this.$rules = {
        'start': [{
            token: "string",
            regex: '".*?"'
        }, {
            token: "string",
            regex: "'.*?'"
        }, {
            token: "constant",
            regex: '[0-9]+'
        }, {
            token: "variable",
            regex: "[-_a-zA-Z0-9:]+"
        }],
        'comment': [{
            token : "comment.block",
            merge: true,
            regex : ".+?"
        }],
        'tag': [{
            token: "entity.name.function",
            regex: "[a-zA-Z][_a-zA-Z0-9]*",
            next: "start"
        }]
    };
};

oop.inherits(DjangoHighlightRules, TextHighlightRules)

var DjangoHtmlHighlightRules = function() {
    this.$rules = new HtmlHighlightRules().getRules();

    for (var i in this.$rules) {
        this.$rules[i].unshift({
            token: "comment.line",
            regex: "\\{#.*?#\\}"
        }, {
            token: "comment.block",
            regex: "\\{\\%\\s*comment\\s*\\%\\}",
            merge: true,
            next: "django-comment"
        }, {
            token: "constant.language",
            regex: "\\{\\{",
            next: "django-start"
        }, {
            token: "constant.language",
            regex: "\\{\\%",
            next: "django-tag"
        });
        this.embedRules(DjangoHighlightRules, "django-", [{
                token: "comment.block",
                regex: "\\{\\%\\s*endcomment\\s*\\%\\}",
                merge: true,
                next: "start"
            }, {
                token: "constant.language",
                regex: "\\%\\}",
                next: "start"
            }, {
                token: "constant.language",
                regex: "\\}\\}",
                next: "start"
        }]);
    }
};

oop.inherits(DjangoHtmlHighlightRules, HtmlHighlightRules);

var Mode = function() {
    HtmlMode.call(this);
    this.HighlightRules = DjangoHtmlHighlightRules;
};
oop.inherits(Mode, HtmlMode);

(function() {
    this.$id = "ace/mode/django";
}).call(Mode.prototype);

exports.Mode = Mode;
});