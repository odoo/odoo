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

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var lang = require("../lib/lang");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var LessHighlightRules = function() {
    
    var properties = lang.arrayToMap( (function () {

        var browserPrefix = ("-webkit-|-moz-|-o-|-ms-|-svg-|-pie-|-khtml-").split("|");
        
        var prefixProperties = ("appearance|background-clip|background-inline-policy|background-origin|" + 
             "background-size|binding|border-bottom-colors|border-left-colors|" + 
             "border-right-colors|border-top-colors|border-end|border-end-color|" + 
             "border-end-style|border-end-width|border-image|border-start|" + 
             "border-start-color|border-start-style|border-start-width|box-align|" + 
             "box-direction|box-flex|box-flexgroup|box-ordinal-group|box-orient|" + 
             "box-pack|box-sizing|column-count|column-gap|column-width|column-rule|" + 
             "column-rule-width|column-rule-style|column-rule-color|float-edge|" + 
             "font-feature-settings|font-language-override|force-broken-image-icon|" + 
             "image-region|margin-end|margin-start|opacity|outline|outline-color|" + 
             "outline-offset|outline-radius|outline-radius-bottomleft|" + 
             "outline-radius-bottomright|outline-radius-topleft|outline-radius-topright|" + 
             "outline-style|outline-width|padding-end|padding-start|stack-sizing|" + 
             "tab-size|text-blink|text-decoration-color|text-decoration-line|" + 
             "text-decoration-style|transform|transform-origin|transition|" + 
             "transition-delay|transition-duration|transition-property|" + 
             "transition-timing-function|user-focus|user-input|user-modify|user-select|" +
             "window-shadow|border-radius").split("|");
        
        var properties = ("azimuth|background-attachment|background-color|background-image|" +
            "background-position|background-repeat|background|border-bottom-color|" +
            "border-bottom-style|border-bottom-width|border-bottom|border-collapse|" +
            "border-color|border-left-color|border-left-style|border-left-width|" +
            "border-left|border-right-color|border-right-style|border-right-width|" +
            "border-right|border-spacing|border-style|border-top-color|" +
            "border-top-style|border-top-width|border-top|border-width|border|" +
            "bottom|box-sizing|caption-side|clear|clip|color|content|counter-increment|" +
            "counter-reset|cue-after|cue-before|cue|cursor|direction|display|" +
            "elevation|empty-cells|float|font-family|font-size-adjust|font-size|" +
            "font-stretch|font-style|font-variant|font-weight|font|height|left|" +
            "letter-spacing|line-height|list-style-image|list-style-position|" +
            "list-style-type|list-style|margin-bottom|margin-left|margin-right|" +
            "margin-top|marker-offset|margin|marks|max-height|max-width|min-height|" +
            "min-width|opacity|orphans|outline-color|" +
            "outline-style|outline-width|outline|overflow|overflow-x|overflow-y|padding-bottom|" +
            "padding-left|padding-right|padding-top|padding|page-break-after|" +
            "page-break-before|page-break-inside|page|pause-after|pause-before|" +
            "pause|pitch-range|pitch|play-during|position|quotes|richness|right|" +
            "size|speak-header|speak-numeral|speak-punctuation|speech-rate|speak|" +
            "stress|table-layout|text-align|text-decoration|text-indent|" +
            "text-shadow|text-transform|top|unicode-bidi|vertical-align|" +
            "visibility|voice-family|volume|white-space|widows|width|word-spacing|" +
            "z-index").split("|");
          
        //The return array     
        var ret = [];
        
        //All prefixProperties will get the browserPrefix in
        //the begning by join the prefixProperties array with the value of browserPrefix
        for (var i=0, ln=browserPrefix.length; i<ln; i++) {
            Array.prototype.push.apply(
                ret,
                (( browserPrefix[i] + prefixProperties.join("|" + browserPrefix[i]) ).split("|"))
            );
        }
        
        //Add also prefixProperties and properties without any browser prefix
        Array.prototype.push.apply(ret, prefixProperties);
        Array.prototype.push.apply(ret, properties);
        
        return ret;
        
    })() );
    


    var functions = lang.arrayToMap(
        ("hsl|hsla|rgb|rgba|url|attr|counter|counters|lighten|darken|saturate|" +
        "desaturate|fadein|fadeout|fade|spin|mix|hue|saturation|lightness|" +
        "alpha|round|ceil|floor|percentage|color|iscolor|isnumber|isstring|" +
        "iskeyword|isurl|ispixel|ispercentage|isem").split("|")
    );

    var constants = lang.arrayToMap(
        ("absolute|all-scroll|always|armenian|auto|baseline|below|bidi-override|" +
        "block|bold|bolder|border-box|both|bottom|break-all|break-word|capitalize|center|" +
        "char|circle|cjk-ideographic|col-resize|collapse|content-box|crosshair|dashed|" +
        "decimal-leading-zero|decimal|default|disabled|disc|" +
        "distribute-all-lines|distribute-letter|distribute-space|" +
        "distribute|dotted|double|e-resize|ellipsis|fixed|georgian|groove|" +
        "hand|hebrew|help|hidden|hiragana-iroha|hiragana|horizontal|" +
        "ideograph-alpha|ideograph-numeric|ideograph-parenthesis|" +
        "ideograph-space|inactive|inherit|inline-block|inline|inset|inside|" +
        "inter-ideograph|inter-word|italic|justify|katakana-iroha|katakana|" +
        "keep-all|left|lighter|line-edge|line-through|line|list-item|loose|" +
        "lower-alpha|lower-greek|lower-latin|lower-roman|lowercase|lr-tb|ltr|" +
        "medium|middle|move|n-resize|ne-resize|newspaper|no-drop|no-repeat|" +
        "nw-resize|none|normal|not-allowed|nowrap|oblique|outset|outside|" +
        "overline|pointer|progress|relative|repeat-x|repeat-y|repeat|right|" +
        "ridge|row-resize|rtl|s-resize|scroll|se-resize|separate|small-caps|" +
        "solid|square|static|strict|super|sw-resize|table-footer-group|" +
        "table-header-group|tb-rl|text-bottom|text-top|text|thick|thin|top|" +
        "transparent|underline|upper-alpha|upper-latin|upper-roman|uppercase|" +
        "vertical-ideographic|vertical-text|visible|w-resize|wait|whitespace|" +
        "zero").split("|")
    );

    var colors = lang.arrayToMap(
        ("aqua|black|blue|fuchsia|gray|green|lime|maroon|navy|olive|orange|" +
        "purple|red|silver|teal|white|yellow").split("|")
    );
    
    var keywords = lang.arrayToMap(
        ("@mixin|@extend|@include|@import|@media|@debug|@warn|@if|@for|@each|" +
        "@while|@else|@font-face|@-webkit-keyframes|if|and|!default|module|" +
        "def|end|declare|when|not|and").split("|")
    );
    
    var tags = lang.arrayToMap(
        ("a|abbr|acronym|address|applet|area|article|aside|audio|b|base|basefont|bdo|" + 
         "big|blockquote|body|br|button|canvas|caption|center|cite|code|col|colgroup|" + 
         "command|datalist|dd|del|details|dfn|dir|div|dl|dt|em|embed|fieldset|" + 
         "figcaption|figure|font|footer|form|frame|frameset|h1|h2|h3|h4|h5|h6|head|" + 
         "header|hgroup|hr|html|i|iframe|img|input|ins|keygen|kbd|label|legend|li|" + 
         "link|map|mark|menu|meta|meter|nav|noframes|noscript|object|ol|optgroup|" + 
         "option|output|p|param|pre|progress|q|rp|rt|ruby|s|samp|script|section|select|" + 
         "small|source|span|strike|strong|style|sub|summary|sup|table|tbody|td|" + 
         "textarea|tfoot|th|thead|time|title|tr|tt|u|ul|var|video|wbr|xmp").split("|")
    );

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    var numRe = "\\-?(?:(?:[0-9]+)|(?:[0-9]*\\.[0-9]+))";

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = {
        "start" : [
            {
                token : "comment",
                regex : "\\/\\/.*$"
            },
            {
                token : "comment", // multi line comment
                regex : "\\/\\*",
                next : "comment"
            }, {
                token : "string", // single line
                regex : '["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
            }, {
                token : "string", // single line
                regex : "['](?:(?:\\\\.)|(?:[^'\\\\]))*?[']"
            }, {
                token : "constant.numeric",
                regex : numRe + "(?:em|ex|px|cm|mm|in|pt|pc|deg|rad|grad|ms|s|hz|khz|%)"
            }, {
                token : "constant.numeric", // hex6 color
                regex : "#[a-f0-9]{6}"
            }, {
                token : "constant.numeric", // hex3 color
                regex : "#[a-f0-9]{3}"
            }, {
                token : "constant.numeric",
                regex : numRe
            }, {
                token : function(value) {
                    if (keywords.hasOwnProperty(value))
                        return "keyword";
                    else
                        return "variable";
                },
                regex : "@[a-z0-9_\\-@]*\\b"
            }, {
                token : function(value) {
                    if (properties.hasOwnProperty(value.toLowerCase()))
                        return "support.type";
                    else if (keywords.hasOwnProperty(value))
                        return "keyword";
                    else if (constants.hasOwnProperty(value))
                        return "constant.language";
                    else if (functions.hasOwnProperty(value))
                        return "support.function";
                    else if (colors.hasOwnProperty(value.toLowerCase()))
                        return "support.constant.color";
                    else if (tags.hasOwnProperty(value.toLowerCase()))
                        return "variable.language";
                    else
                        return "text";
                },
                regex : "\\-?[@a-z_][@a-z0-9_\\-]*"
            }, {
                token: "variable.language",
                regex: "#[a-z0-9-_]+"
            }, {
                token: "variable.language",
                regex: "\\.[a-z0-9-_]+"
            }, {
                token: "variable.language",
                regex: ":[a-z_][a-z0-9-_]*"
            }, {
                token: "constant",
                regex: "[a-z0-9-_]+"
            }, {
                token : "keyword.operator",
                regex : "<|>|<=|>=|==|!=|-|%|#|\\+|\\$|\\+|\\*"
            }, {
                token : "paren.lparen",
                regex : "[[({]"
            }, {
                token : "paren.rparen",
                regex : "[\\])}]"
            }, {
                token : "text",
                regex : "\\s+"
            }, {
                caseInsensitive: true
            }
        ],
        "comment" : [
            {
                token : "comment", // closing comment
                regex : ".*?\\*\\/",
                next : "start"
            }, {
                token : "comment", // comment spanning whole line
                regex : ".+"
            }
        ]
    };
};

oop.inherits(LessHighlightRules, TextHighlightRules);

exports.LessHighlightRules = LessHighlightRules;

});
