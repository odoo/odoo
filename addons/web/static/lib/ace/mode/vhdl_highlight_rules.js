/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2013, Ajax.org B.V.
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
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var VHDLHighlightRules = function() {


    
    var keywords = "access|after|ailas|all|architecture|assert|attribute|"+
                   "begin|block|buffer|bus|case|component|configuration|"+
                   "disconnect|downto|else|elsif|end|entity|file|for|function|"+
                   "generate|generic|guarded|if|impure|in|inertial|inout|is|"+
                   "label|linkage|literal|loop|mapnew|next|of|on|open|"+
                   "others|out|port|process|pure|range|record|reject|"+
                   "report|return|select|shared|subtype|then|to|transport|"+
                   "type|unaffected|united|until|wait|when|while|with";
    
    var storageType = "bit|bit_vector|boolean|character|integer|line|natural|"+
                      "positive|real|register|severity|signal|signed|"+
                      "std_logic|std_logic_vector|string||text|time|unsigned|"+
                      "variable";
    
    var storageModifiers = "array|constant";
    
    var keywordOperators = "abs|and|mod|nand|nor|not|rem|rol|ror|sla|sll|sra"+
                           "srl|xnor|xor";
    
    var builtinConstants = (
        "true|false|null"
    );


    var keywordMapper = this.createKeywordMapper({
        "keyword.operator": keywordOperators,
        "keyword": keywords,
        "constant.language": builtinConstants,
        "storage.modifier": storageModifiers,
        "storage.type": storageType
    }, "identifier", true);

    this.$rules = {
        "start" : [ {
            token : "comment",
            regex : "--.*$"
        }, {
            token : "string",           // " string
            regex : '".*?"'
        }, {
            token : "string",           // ' string
            regex : "'.*?'"
        }, {
            token : "constant.numeric", // float
            regex : "[+-]?\\d+(?:(?:\\.\\d*)?(?:[eE][+-]?\\d+)?)?\\b"
        }, {
            token : "keyword", // pre-compiler directives
            regex : "\\s*(?:library|package|use)\\b",
        }, {
            token : keywordMapper,
            regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
        }, {
            token : "keyword.operator",
            regex : "&|\\*|\\+|\\-|\\/|<|=|>|\\||=>|\\*\\*|:=|\\/=|>=|<=|<>" 
        }, {
              token : "punctuation.operator",
              regex : "\\'|\\:|\\,|\\;|\\."
        },{
            token : "paren.lparen",
            regex : "[[(]"
        }, {
            token : "paren.rparen",
            regex : "[\\])]"
        }, {
            token : "text",
            regex : "\\s+"
        } ],

       
    };
};

oop.inherits(VHDLHighlightRules, TextHighlightRules);

exports.VHDLHighlightRules = VHDLHighlightRules;
});
