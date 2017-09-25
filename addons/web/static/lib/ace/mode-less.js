(function() {var define = ace.define, require = ace.require;
define("ace/mode/less", ["require", "exports", "module", "ace/lib/oop", "ace/mode/text", "ace/tokenizer", "ace/mode/less_highlight_rules", "ace/mode/matching_brace_outdent", "ace/mode/folding/cstyle"], function(e, t) {
    var r = e("../lib/oop"),
        o = e("./text").Mode,
        n = e("../tokenizer").Tokenizer,
        i = e("./less_highlight_rules").LessHighlightRules,
        a = e("./matching_brace_outdent").MatchingBraceOutdent,
        l = e("./folding/cstyle").FoldMode,
        s = function() {
            this.$tokenizer = new n((new i).getRules(), "i"), this.$outdent = new a, this.foldingRules = new l
        };
    r.inherits(s, o),
        function() {
            this.getNextLineIndent = function(e, t, r) {
                var o = this.$getIndent(t),
                    n = this.$tokenizer.getLineTokens(t, e).tokens;
                if (n.length && "comment" == n[n.length - 1].type) return o;
                var i = t.match(/^.*\{\s*$/);
                return i && (o += r), o
            }, this.checkOutdent = function(e, t, r) {
                return this.$outdent.checkOutdent(t, r)
            }, this.autoOutdent = function(e, t, r) {
                this.$outdent.autoOutdent(t, r)
            }
        }.call(s.prototype), t.Mode = s
}), define("ace/mode/less_highlight_rules", ["require", "exports", "module", "ace/lib/oop", "ace/lib/lang", "ace/mode/text_highlight_rules"], function(e, t) {
    var r = e("../lib/oop"),
        o = e("../lib/lang"),
        n = e("./text_highlight_rules").TextHighlightRules,
        i = function() {
            var e = o.arrayToMap(function() {
                    for (var e = "-webkit-|-moz-|-o-|-ms-|-svg-|-pie-|-khtml-".split("|"), t = "appearance|background-clip|background-inline-policy|background-origin|background-size|binding|border-bottom-colors|border-left-colors|border-right-colors|border-top-colors|border-end|border-end-color|border-end-style|border-end-width|border-image|border-start|border-start-color|border-start-style|border-start-width|box-align|box-direction|box-flex|box-flexgroup|box-ordinal-group|box-orient|box-pack|box-sizing|column-count|column-gap|column-width|column-rule|column-rule-width|column-rule-style|column-rule-color|float-edge|font-feature-settings|font-language-override|force-broken-image-icon|image-region|margin-end|margin-start|opacity|outline|outline-color|outline-offset|outline-radius|outline-radius-bottomleft|outline-radius-bottomright|outline-radius-topleft|outline-radius-topright|outline-style|outline-width|padding-end|padding-start|stack-sizing|tab-size|text-blink|text-decoration-color|text-decoration-line|text-decoration-style|transform|transform-origin|transition|transition-delay|transition-duration|transition-property|transition-timing-function|user-focus|user-input|user-modify|user-select|window-shadow|border-radius".split("|"), r = "azimuth|background-attachment|background-color|background-image|background-position|background-repeat|background|border-bottom-color|border-bottom-style|border-bottom-width|border-bottom|border-collapse|border-color|border-left-color|border-left-style|border-left-width|border-left|border-right-color|border-right-style|border-right-width|border-right|border-spacing|border-style|border-top-color|border-top-style|border-top-width|border-top|border-width|border|bottom|box-sizing|caption-side|clear|clip|color|content|counter-increment|counter-reset|cue-after|cue-before|cue|cursor|direction|display|elevation|empty-cells|float|font-family|font-size-adjust|font-size|font-stretch|font-style|font-variant|font-weight|font|height|left|letter-spacing|line-height|list-style-image|list-style-position|list-style-type|list-style|margin-bottom|margin-left|margin-right|margin-top|marker-offset|margin|marks|max-height|max-width|min-height|min-width|opacity|orphans|outline-color|outline-style|outline-width|outline|overflow|overflow-x|overflow-y|padding-bottom|padding-left|padding-right|padding-top|padding|page-break-after|page-break-before|page-break-inside|page|pause-after|pause-before|pause|pitch-range|pitch|play-during|position|quotes|richness|right|size|speak-header|speak-numeral|speak-punctuation|speech-rate|speak|stress|table-layout|text-align|text-decoration|text-indent|text-shadow|text-transform|top|unicode-bidi|vertical-align|visibility|voice-family|volume|white-space|widows|width|word-spacing|z-index".split("|"), o = [], n = 0, i = e.length; i > n; n++) Array.prototype.push.apply(o, (e[n] + t.join("|" + e[n])).split("|"));
                    return Array.prototype.push.apply(o, t), Array.prototype.push.apply(o, r), o
                }()),
                t = o.arrayToMap("hsl|hsla|rgb|rgba|url|attr|counter|counters|lighten|darken|saturate|desaturate|fadein|fadeout|fade|spin|mix|hue|saturation|lightness|alpha|round|ceil|floor|percentage|color|iscolor|isnumber|isstring|iskeyword|isurl|ispixel|ispercentage|isem".split("|")),
                r = o.arrayToMap("absolute|all-scroll|always|armenian|auto|baseline|below|bidi-override|block|bold|bolder|border-box|both|bottom|break-all|break-word|capitalize|center|char|circle|cjk-ideographic|col-resize|collapse|content-box|crosshair|dashed|decimal-leading-zero|decimal|default|disabled|disc|distribute-all-lines|distribute-letter|distribute-space|distribute|dotted|double|e-resize|ellipsis|fixed|georgian|groove|hand|hebrew|help|hidden|hiragana-iroha|hiragana|horizontal|ideograph-alpha|ideograph-numeric|ideograph-parenthesis|ideograph-space|inactive|inherit|inline-block|inline|inset|inside|inter-ideograph|inter-word|italic|justify|katakana-iroha|katakana|keep-all|left|lighter|line-edge|line-through|line|list-item|loose|lower-alpha|lower-greek|lower-latin|lower-roman|lowercase|lr-tb|ltr|medium|middle|move|n-resize|ne-resize|newspaper|no-drop|no-repeat|nw-resize|none|normal|not-allowed|nowrap|oblique|outset|outside|overline|pointer|progress|relative|repeat-x|repeat-y|repeat|right|ridge|row-resize|rtl|s-resize|scroll|se-resize|separate|small-caps|solid|square|static|strict|super|sw-resize|table-footer-group|table-header-group|tb-rl|text-bottom|text-top|text|thick|thin|top|transparent|underline|upper-alpha|upper-latin|upper-roman|uppercase|vertical-ideographic|vertical-text|visible|w-resize|wait|whitespace|zero".split("|")),
                n = o.arrayToMap("aqua|black|blue|fuchsia|gray|green|lime|maroon|navy|olive|orange|purple|red|silver|teal|white|yellow".split("|")),
                i = o.arrayToMap("@mixin|@extend|@include|@import|@media|@debug|@warn|@if|@for|@each|@while|@else|@font-face|@-webkit-keyframes|if|and|!default|module|def|end|declare|when|not|and".split("|")),
                a = o.arrayToMap("a|abbr|acronym|address|applet|area|article|aside|audio|b|base|basefont|bdo|big|blockquote|body|br|button|canvas|caption|center|cite|code|col|colgroup|command|datalist|dd|del|details|dfn|dir|div|dl|dt|em|embed|fieldset|figcaption|figure|font|footer|form|frame|frameset|h1|h2|h3|h4|h5|h6|head|header|hgroup|hr|html|i|iframe|img|input|ins|keygen|kbd|label|legend|li|link|map|mark|menu|meta|meter|nav|noframes|noscript|object|ol|optgroup|option|output|p|param|pre|progress|q|rp|rt|ruby|s|samp|script|section|select|small|source|span|strike|strong|style|sub|summary|sup|table|tbody|td|textarea|tfoot|th|thead|time|title|tr|tt|u|ul|var|video|wbr|xmp".split("|")),
                l = "\\-?(?:(?:[0-9]+)|(?:[0-9]*\\.[0-9]+))";
            this.$rules = {
                start: [{
                    token: "comment",
                    regex: "\\/\\/.*$"
                }, {
                    token: "comment",
                    merge: !0,
                    regex: "\\/\\*",
                    next: "comment"
                }, {
                    token: "string",
                    regex: '["](?:(?:\\\\.)|(?:[^"\\\\]))*?["]'
                }, {
                    token: "string",
                    regex: "['](?:(?:\\\\.)|(?:[^'\\\\]))*?[']"
                }, {
                    token: "constant.numeric",
                    regex: l + "(?:em|ex|px|cm|mm|in|pt|pc|deg|rad|grad|ms|s|hz|khz|%)"
                }, {
                    token: "constant.numeric",
                    regex: "#[a-f0-9]{6}"
                }, {
                    token: "constant.numeric",
                    regex: "#[a-f0-9]{3}"
                }, {
                    token: "constant.numeric",
                    regex: l
                }, {
                    token: function(e) {
                        return i.hasOwnProperty(e) ? "keyword" : "variable"
                    },
                    regex: "@[a-z0-9_\\-@]*\\b"
                }, {
                    token: function(o) {
                        return e.hasOwnProperty(o.toLowerCase()) ? "support.type" : i.hasOwnProperty(o) ? "keyword" : r.hasOwnProperty(o) ? "constant.language" : t.hasOwnProperty(o) ? "support.function" : n.hasOwnProperty(o.toLowerCase()) ? "support.constant.color" : a.hasOwnProperty(o.toLowerCase()) ? "variable.language" : "text"
                    },
                    regex: "\\-?[@a-z_][@a-z0-9_\\-]*"
                }, {
                    token: "variable.language",
                    regex: "#[a-z0-9-_]+"
                }, {
                    token: "variable.language",
                    regex: "\\.[a-z0-9-_]+"
                }, {
                    token: "variable.language",
                    regex: ":[a-z0-9-_]+"
                }, {
                    token: "constant",
                    regex: "[a-z0-9-_]+"
                }, {
                    token: "keyword.operator",
                    regex: "<|>|<=|>=|==|!=|-|%|#|\\+|\\$|\\+|\\*"
                }, {
                    token: "paren.lparen",
                    regex: "[[({]"
                }, {
                    token: "paren.rparen",
                    regex: "[\\])}]"
                }, {
                    token: "text",
                    regex: "\\s+"
                }],
                comment: [{
                    token: "comment",
                    regex: ".*?\\*\\/",
                    next: "start"
                }, {
                    token: "comment",
                    merge: !0,
                    regex: ".+"
                }]
            }
        };
    r.inherits(i, n), t.LessHighlightRules = i
}), define("ace/mode/matching_brace_outdent", ["require", "exports", "module", "ace/range"], function(e, t) {
    var r = e("../range").Range,
        o = function() {};
    (function() {
        this.checkOutdent = function(e, t) {
            return /^\s+$/.test(e) ? /^\s*\}/.test(t) : !1
        }, this.autoOutdent = function(e, t) {
            var o = e.getLine(t),
                n = o.match(/^(\s*\})/);
            if (!n) return 0;
            var i = n[1].length,
                a = e.findMatchingBracket({
                    row: t,
                    column: i
                });
            if (!a || a.row == t) return 0;
            var l = this.$getIndent(e.getLine(a.row));
            e.replace(new r(t, 0, t, i - 1), l)
        }, this.$getIndent = function(e) {
            var t = e.match(/^(\s+)/);
            return t ? t[1] : ""
        }
    }).call(o.prototype), t.MatchingBraceOutdent = o
}), define("ace/mode/folding/cstyle", ["require", "exports", "module", "ace/lib/oop", "ace/range", "ace/mode/folding/fold_mode"], function(e, t) {
    var r = e("../../lib/oop"),
        o = e("../../range").Range,
        n = e("./fold_mode").FoldMode,
        i = t.FoldMode = function() {};
    r.inherits(i, n),
        function() {
            this.foldingStartMarker = /(\{|\[)[^\}\]]*$|^\s*(\/\*)/, this.foldingStopMarker = /^[^\[\{]*(\}|\])|^[\s\*]*(\*\/)/, this.getFoldWidgetRange = function(e, t, r) {
                var n = e.getLine(r),
                    i = n.match(this.foldingStartMarker);
                if (i) {
                    var a = i.index;
                    if (i[1]) return this.openingBracketBlock(e, i[1], r, a);
                    var l = e.getCommentFoldRange(r, a + i[0].length);
                    return l.end.column -= 2, l
                }
                if ("markbeginend" === t) {
                    var i = n.match(this.foldingStopMarker);
                    if (i) {
                        var a = i.index + i[0].length;
                        if (i[2]) {
                            var l = e.getCommentFoldRange(r, a);
                            return l.end.column -= 2, l
                        }
                        var s = {
                                row: r,
                                column: a
                            },
                            d = e.$findOpeningBracket(i[1], s);
                        if (!d) return;
                        return d.column++, s.column--, o.fromPoints(d, s)
                    }
                }
            }
        }.call(i.prototype)
}), define("ace/mode/folding/fold_mode", ["require", "exports", "module", "ace/range"], function(e, t) {
    var r = e("../../range").Range,
        o = t.FoldMode = function() {};
    (function() {
        this.foldingStartMarker = null, this.foldingStopMarker = null, this.getFoldWidget = function(e, t, r) {
            var o = e.getLine(r);
            return this.foldingStartMarker.test(o) ? "start" : "markbeginend" == t && this.foldingStopMarker && this.foldingStopMarker.test(o) ? "end" : ""
        }, this.getFoldWidgetRange = function() {
            return null
        }, this.indentationBlock = function(e, t, o) {
            for (var n = /^\s*/, i = t, a = t, l = e.getLine(t), s = o || l.length, d = l.match(n)[0].length, c = e.getLength(); ++t < c;) {
                l = e.getLine(t);
                var g = l.match(n)[0].length;
                if (g != l.length) {
                    if (d >= g) break;
                    a = t
                }
            }
            if (a > i) {
                var u = e.getLine(a).length;
                return new r(i, s, a, u)
            }
        }, this.openingBracketBlock = function(e, t, o, n, i, a) {
            var l = {
                    row: o,
                    column: n + 1
                },
                s = e.$findClosingBracket(t, l, i, a);
            if (s) {
                var d = e.foldWidgets[s.row];
                return null == d && (d = this.getFoldWidget(e, s.row)), "start" == d && (s.row--, s.column = e.getLine(s.row).length), r.fromPoints(l, s)
            }
        }
    }).call(o.prototype)
});
})();
