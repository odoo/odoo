define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var lang = require("../lib/lang");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
var DocCommentHighlightRules = require("./doc_comment_highlight_rules").DocCommentHighlightRules;

var DotHighlightRules = function() {

   var keywords = lang.arrayToMap(
        ("strict|node|edge|graph|digraph|subgraph").split("|")
   );

   var attributes = lang.arrayToMap(
        ("damping|k|url|area|arrowhead|arrowsize|arrowtail|aspect|bb|bgcolor|center|charset|clusterrank|color|colorscheme|comment|compound|concentrate|constraint|decorate|defaultdist|dim|dimen|dir|diredgeconstraints|distortion|dpi|edgeurl|edgehref|edgetarget|edgetooltip|epsilon|esep|fillcolor|fixedsize|fontcolor|fontname|fontnames|fontpath|fontsize|forcelabels|gradientangle|group|headurl|head_lp|headclip|headhref|headlabel|headport|headtarget|headtooltip|height|href|id|image|imagepath|imagescale|label|labelurl|label_scheme|labelangle|labeldistance|labelfloat|labelfontcolor|labelfontname|labelfontsize|labelhref|labeljust|labelloc|labeltarget|labeltooltip|landscape|layer|layerlistsep|layers|layerselect|layersep|layout|len|levels|levelsgap|lhead|lheight|lp|ltail|lwidth|margin|maxiter|mclimit|mindist|minlen|mode|model|mosek|nodesep|nojustify|normalize|nslimit|nslimit1|ordering|orientation|outputorder|overlap|overlap_scaling|pack|packmode|pad|page|pagedir|pencolor|penwidth|peripheries|pin|pos|quadtree|quantum|rank|rankdir|ranksep|ratio|rects|regular|remincross|repulsiveforce|resolution|root|rotate|rotation|samehead|sametail|samplepoints|scale|searchsize|sep|shape|shapefile|showboxes|sides|size|skew|smoothing|sortv|splines|start|style|stylesheet|tailurl|tail_lp|tailclip|tailhref|taillabel|tailport|tailtarget|tailtooltip|target|tooltip|truecolor|vertices|viewport|voro_margin|weight|width|xlabel|xlp|z").split("|")
   );

   this.$rules = {
        "start" : [
            {
                token : "comment",
                regex : /\/\/.*$/
            }, {
                token : "comment",
                regex : /#.*$/
            }, {
                token : "comment", // multi line comment
                merge : true,
                regex : /\/\*/,
                next : "comment"
            }, {
                token : "string",
                regex : "'(?=.)",
                next  : "qstring"
            }, {
                token : "string",
                regex : '"(?=.)',
                next  : "qqstring"
            }, {
                token : "constant.numeric",
                regex : /[+\-]?\d+(?:(?:\.\d*)?(?:[eE][+\-]?\d+)?)?\b/
            }, {
                token : "keyword.operator",
                regex : /\+|=|\->/
            }, {
                token : "punctuation.operator",
                regex : /,|;/
            }, {
                token : "paren.lparen",
                regex : /[\[{]/
            }, {
                token : "paren.rparen",
                regex : /[\]}]/
            }, {
                token: "comment",
                regex: /^#!.*$/
            }, {
                token: function(value) {
                    if (keywords.hasOwnProperty(value.toLowerCase())) {
                        return "keyword";
                    }
                    else if (attributes.hasOwnProperty(value.toLowerCase())) {
                        return "variable";
                    }
                    else {
                        return "text";
                    }
                },
                regex: "\\-?[a-zA-Z_][a-zA-Z0-9_\\-]*"
           }
        ],
        "comment" : [
            {
                token : "comment", // closing comment
                regex : ".*?\\*\\/",
                merge : true,
                next : "start"
            }, {
                token : "comment", // comment spanning whole line
                merge : true,
                regex : ".+"
            }
        ],
        "qqstring" : [
            {
                token : "string",
                regex : '[^"\\\\]+',
                merge : true
            }, {
                token : "string",
                regex : "\\\\$",
                next  : "qqstring",
                merge : true
            }, {
                token : "string",
                regex : '"|$',
                next  : "start",
                merge : true
            }
        ],
        "qstring" : [
            {
                token : "string",
                regex : "[^'\\\\]+",
                merge : true
            }, {
                token : "string",
                regex : "\\\\$",
                next  : "qstring",
                merge : true
            }, {
                token : "string",
                regex : "'|$",
                next  : "start",
                merge : true
            }
        ]
   };
};

oop.inherits(DotHighlightRules, TextHighlightRules);

exports.DotHighlightRules = DotHighlightRules;

});
