/*
 * MUSHCodeMode
 */

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var MushCodeRules = function() {


    var keywords = (
 "@if|"+
 "@ifelse|"+
 "@switch|"+
 "@halt|"+
 "@dolist|"+
 "@create|"+
 "@scent|"+
 "@sound|"+
 "@touch|"+
 "@ataste|"+
 "@osound|"+
 "@ahear|"+
 "@aahear|"+
 "@amhear|"+
 "@otouch|"+
 "@otaste|"+
 "@drop|"+
 "@odrop|"+
 "@adrop|"+
 "@dropfail|"+
 "@odropfail|"+
 "@smell|"+
 "@oemit|"+
 "@emit|"+
 "@pemit|"+
 "@parent|"+
 "@clone|"+
 "@taste|"+
 "whisper|"+
 "page|"+
 "say|"+
 "pose|"+
 "semipose|"+
 "teach|"+
 "touch|"+
 "taste|"+
 "smell|"+
 "listen|"+
 "look|"+
 "move|"+
 "go|"+
 "home|"+
 "follow|"+
 "unfollow|"+
 "desert|"+
 "dismiss|"+
 "@tel"
    );

    var builtinConstants = (
        "=#0"
    );

    var builtinFunctions = (
 "default|"+
 "edefault|"+
 "eval|"+
 "get_eval|"+
 "get|"+
 "grep|"+
 "grepi|"+
 "hasattr|"+
 "hasattrp|"+
 "hasattrval|"+
 "hasattrpval|"+
 "lattr|"+
 "nattr|"+
 "poss|"+
 "udefault|"+
 "ufun|"+
 "u|"+
 "v|"+
 "uldefault|"+
 "xget|"+
 "zfun|"+
 "band|"+
 "bnand|"+
 "bnot|"+
 "bor|"+
 "bxor|"+
 "shl|"+
 "shr|"+
 "and|"+
 "cand|"+
 "cor|"+
 "eq|"+
 "gt|"+
 "gte|"+
 "lt|"+
 "lte|"+
 "nand|"+
 "neq|"+
 "nor|"+
 "not|"+
 "or|"+
 "t|"+
 "xor|"+
 "con|"+
 "entrances|"+
 "exit|"+
 "followers|"+
 "home|"+
 "lcon|"+
 "lexits|"+
 "loc|"+
 "locate|"+
 "lparent|"+
 "lsearch|"+
 "next|"+
 "num|"+
 "owner|"+
 "parent|"+
 "pmatch|"+
 "rloc|"+
 "rnum|"+
 "room|"+
 "where|"+
 "zone|"+
 "worn|"+
 "held|"+
 "carried|"+
 "acos|"+
 "asin|"+
 "atan|"+
 "ceil|"+
 "cos|"+
 "e|"+
 "exp|"+
 "fdiv|"+
 "fmod|"+
 "floor|"+
 "log|"+
 "ln|"+
 "pi|"+
 "power|"+
 "round|"+
 "sin|"+
 "sqrt|"+
 "tan|"+
 "aposs|"+
 "andflags|"+
 "conn|"+
 "commandssent|"+
 "controls|"+
 "doing|"+
 "elock|"+
 "findable|"+
 "flags|"+
 "fullname|"+
 "hasflag|"+
 "haspower|"+
 "hastype|"+
 "hidden|"+
 "idle|"+
 "isbaker|"+
 "lock|"+
 "lstats|"+
 "money|"+
 "who|"+
 "name|"+
 "nearby|"+
 "obj|"+
 "objflags|"+
 "photo|"+
 "poll|"+
 "powers|"+
 "pendingtext|"+
 "receivedtext|"+
 "restarts|"+
 "restarttime|"+
 "subj|"+
 "shortestpath|"+
 "tmoney|"+
 "type|"+
 "visible|"+
 "cat|"+
 "element|"+
 "elements|"+
 "extract|"+
 "filter|"+
 "filterbool|"+
 "first|"+
 "foreach|"+
 "fold|"+
 "grab|"+
 "graball|"+
 "index|"+
 "insert|"+
 "itemize|"+
 "items|"+
 "iter|"+
 "last|"+
 "ldelete|"+
 "map|"+
 "match|"+
 "matchall|"+
 "member|"+
 "mix|"+
 "munge|"+
 "pick|"+
 "remove|"+
 "replace|"+
 "rest|"+
 "revwords|"+
 "setdiff|"+
 "setinter|"+
 "setunion|"+
 "shuffle|"+
 "sort|"+
 "sortby|"+
 "splice|"+
 "step|"+
 "wordpos|"+
 "words|"+
 "add|"+
 "lmath|"+
 "max|"+
 "mean|"+
 "median|"+
 "min|"+
 "mul|"+
 "percent|"+
 "sign|"+
 "stddev|"+
 "sub|"+
 "val|"+
 "bound|"+
 "abs|"+
 "inc|"+
 "dec|"+
 "dist2d|"+
 "dist3d|"+
 "div|"+
 "floordiv|"+
 "mod|"+
 "modulo|"+
 "remainder|"+
 "vadd|"+
 "vdim|"+
 "vdot|"+
 "vmag|"+
 "vmax|"+
 "vmin|"+
 "vmul|"+
 "vsub|"+
 "vunit|"+
 "regedit|"+
 "regeditall|"+
 "regeditalli|"+
 "regediti|"+
 "regmatch|"+
 "regmatchi|"+
 "regrab|"+
 "regraball|"+
 "regraballi|"+
 "regrabi|"+
 "regrep|"+
 "regrepi|"+
 "after|"+
 "alphamin|"+
 "alphamax|"+
 "art|"+
 "before|"+
 "brackets|"+
 "capstr|"+
 "case|"+
 "caseall|"+
 "center|"+
 "containsfansi|"+
 "comp|"+
 "decompose|"+
 "decrypt|"+
 "delete|"+
 "edit|"+
 "encrypt|"+
 "escape|"+
 "if|"+
 "ifelse|"+
 "lcstr|"+
 "left|"+
 "lit|"+
 "ljust|"+
 "merge|"+
 "mid|"+
 "ostrlen|"+
 "pos|"+
 "repeat|"+
 "reverse|"+
 "right|"+
 "rjust|"+
 "scramble|"+
 "secure|"+
 "space|"+
 "spellnum|"+
 "squish|"+
 "strcat|"+
 "strmatch|"+
 "strinsert|"+
 "stripansi|"+
 "stripfansi|"+
 "strlen|"+
 "switch|"+
 "switchall|"+
 "table|"+
 "tr|"+
 "trim|"+
 "ucstr|"+
 "unsafe|"+
 "wrap|"+
 "ctitle|"+
 "cwho|"+
 "channels|"+
 "clock|"+
 "cflags|"+
 "ilev|"+
 "itext|"+
 "inum|"+
 "convsecs|"+
 "convutcsecs|"+
 "convtime|"+
 "ctime|"+
 "etimefmt|"+
 "isdaylight|"+
 "mtime|"+
 "secs|"+
 "msecs|"+
 "starttime|"+
 "time|"+
 "timefmt|"+
 "timestring|"+
 "utctime|"+
 "atrlock|"+
 "clone|"+
 "create|"+
 "cook|"+
 "dig|"+
 "emit|"+
 "lemit|"+
 "link|"+
 "oemit|"+
 "open|"+
 "pemit|"+
 "remit|"+
 "set|"+
 "tel|"+
 "wipe|"+
 "zemit|"+
 "fbcreate|"+
 "fbdestroy|"+
 "fbwrite|"+
 "fbclear|"+
 "fbcopy|"+
 "fbcopyto|"+
 "fbclip|"+
 "fbdump|"+
 "fbflush|"+
 "fbhset|"+
 "fblist|"+
 "fbstats|"+
 "qentries|"+
 "qentry|"+
 "play|"+
 "ansi|"+
 "break|"+
 "c|"+
 "asc|"+
 "die|"+
 "isdbref|"+
 "isint|"+
 "isnum|"+
 "isletters|"+
 "linecoords|"+
 "localize|"+
 "lnum|"+
 "nameshort|"+
 "null|"+
 "objeval|"+
 "r|"+
 "rand|"+
 "s|"+
 "setq|"+
 "setr|"+
 "soundex|"+
 "soundslike|"+
 "valid|"+
 "vchart|"+
 "vchart2|"+
 "vlabel|"+
 "@@|"+
 "bakerdays|"+
 "bodybuild|"+
 "box|"+
 "capall|"+
 "catalog|"+
 "children|"+
 "ctrailer|"+
 "darttime|"+
 "debt|"+
 "detailbar|"+
 "exploredroom|"+
 "fansitoansi|"+
 "fansitoxansi|"+
 "fullbar|"+
 "halfbar|"+
 "isdarted|"+
 "isnewbie|"+
 "isword|"+
 "lambda|"+
 "lobjects|"+
 "lplayers|"+
 "lthings|"+
 "lvexits|"+
 "lvobjects|"+
 "lvplayers|"+
 "lvthings|"+
 "newswrap|"+
 "numsuffix|"+
 "playerson|"+
 "playersthisweek|"+
 "randomad|"+
 "randword|"+
 "realrandword|"+
 "replacechr|"+
 "second|"+
 "splitamount|"+
 "strlenall|"+
 "text|"+
 "third|"+
 "tofansi|"+
 "totalac|"+
 "unique|"+
 "getaddressroom|"+
 "listpropertycomm|"+
 "listpropertyres|"+
 "lotowner|"+
 "lotrating|"+
 "lotratingcount|"+
 "lotvalue|"+
 "boughtproduct|"+
 "companyabb|"+
 "companyicon|"+
 "companylist|"+
 "companyname|"+
 "companyowners|"+
 "companyvalue|"+
 "employees|"+
 "invested|"+
 "productlist|"+
 "productname|"+
 "productowners|"+
 "productrating|"+
 "productratingcount|"+
 "productsoldat|"+
 "producttype|"+
 "ratedproduct|"+
 "soldproduct|"+
 "topproducts|"+
 "totalspentonproduct|"+
 "totalstock|"+
 "transfermoney|"+
 "uniquebuyercount|"+
 "uniqueproductsbought|"+
 "validcompany|"+
 "deletepicture|"+
 "fbsave|"+
 "getpicturesecurity|"+
 "haspicture|"+
 "listpictures|"+
 "picturesize|"+
 "replacecolor|"+
 "rgbtocolor|"+
 "savepicture|"+
 "setpicturesecurity|"+
 "showpicture|"+
 "piechart|"+
 "piechartlabel|"+
 "createmaze|"+
 "drawmaze|"+
 "drawwireframe"
    );
    var keywordMapper = this.createKeywordMapper({
        "invalid.deprecated": "debugger",
        "support.function": builtinFunctions,
        "constant.language": builtinConstants,
        "keyword": keywords
    }, "identifier");

    var strPre = "(?:r|u|ur|R|U|UR|Ur|uR)?";

    var decimalInteger = "(?:(?:[1-9]\\d*)|(?:0))";
    var octInteger = "(?:0[oO]?[0-7]+)";
    var hexInteger = "(?:0[xX][\\dA-Fa-f]+)";
    var binInteger = "(?:0[bB][01]+)";
    var integer = "(?:" + decimalInteger + "|" + octInteger + "|" + hexInteger + "|" + binInteger + ")";

    var exponent = "(?:[eE][+-]?\\d+)";
    var fraction = "(?:\\.\\d+)";
    var intPart = "(?:\\d+)";
    var pointFloat = "(?:(?:" + intPart + "?" + fraction + ")|(?:" + intPart + "\\.))";
    var exponentFloat = "(?:(?:" + pointFloat + "|" +  intPart + ")" + exponent + ")";
    var floatNumber = "(?:" + exponentFloat + "|" + pointFloat + ")";

    this.$rules = {
        "start" : [
         {
                token : "variable", // mush substitution register
                regex : "%[0-9]{1}"
         },
         {
                token : "variable", // mush substitution register
                regex : "%q[0-9A-Za-z]{1}"
         },
         {
                token : "variable", // mush special character register
                regex : "%[a-zA-Z]{1}"
         },
         {
                token: "variable.language",
                regex: "%[a-z0-9-_]+"
         },
        {
            token : "constant.numeric", // imaginary
            regex : "(?:" + floatNumber + "|\\d+)[jJ]\\b"
        }, {
            token : "constant.numeric", // float
            regex : floatNumber
        }, {
            token : "constant.numeric", // long integer
            regex : integer + "[lL]\\b"
        }, {
            token : "constant.numeric", // integer
            regex : integer + "\\b"
        }, {
            token : keywordMapper,
            regex : "[a-zA-Z_$][a-zA-Z0-9_$]*\\b"
        }, {
            token : "keyword.operator",
            regex : "\\+|\\-|\\*|\\*\\*|\\/|\\/\\/|#|%|<<|>>|\\||\\^|~|<|>|<=|=>|==|!=|<>|="
        }, {
            token : "paren.lparen",
            regex : "[\\[\\(\\{]"
        }, {
            token : "paren.rparen",
            regex : "[\\]\\)\\}]"
        }, {
            token : "text",
            regex : "\\s+"
        } ]
    };
};

oop.inherits(MushCodeRules, TextHighlightRules);

exports.MushCodeRules = MushCodeRules;
});
