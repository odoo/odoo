define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var PraatHighlightRules = function() {

    var keywords = (
        "if|then|else|elsif|elif|endif|fi|" +
        "endfor|endproc|" + // related keywords specified below
        "while|endwhile|" +
        "repeat|until|" +
        "select|plus|minus|" +
        "assert|asserterror"
    );

    var predefinedVariables = (
        "macintosh|windows|unix|" +
        "praatVersion|praatVersion\\$" +
        "pi|undefined|" +
        "newline\\$|tab\\$|" +
        "shellDirectory\\$|homeDirectory\\$|preferencesDirectory\\$|" +
        "temporaryDirectory\\$|defaultDirectory\\$"
    );

    // What is "endSendPraat"? Function? Directive?
    var directives = (
        "clearinfo|endSendPraat"
    );

    var functions = (
//      Info functions
        "writeInfo|writeInfoLine|appendInfo|appendInfoLine|info\\$|" +
        "writeFile|writeFileLine|appendFile|appendFileLine|" +
//      Math functions
        "abs|round|floor|ceiling|min|max|imin|imax|" +
        "sqrt|sin|cos|tan|arcsin|arccos|arctan|arctan2|sinc|sincpi|" +
        "exp|ln|lnBeta|lnGamma|log10|log2|" +
        "sinh|cosh|tanh|arcsinh|arccosh|arctanh|" +
        "sigmoid|invSigmoid|erf|erfc|" +
        "random(?:Uniform|Integer|Gauss|Poisson|Binomial)|" +
        "gaussP|gaussQ|invGaussQ|incompleteGammaP|incompleteBeta|" +
        "chiSquareP|chiSquareQ|invChiSquareQ|studentP|studentQ|invStudentQ|" +
        "fisherP|fisherQ|invFisherQ|" +
        "binomialP|binomialQ|invBinomialP|invBinomialQ|" +
        "hertzToBark|barkToHerz|" +
        "hertzToMel|melToHertz|" +
        "hertzToSemitones|semitonesToHerz|" +
        "erb|hertzToErb|erbToHertz|" +
        "phonToDifferenceLimens|differenceLimensToPhon|" +
        "soundPressureToPhon|" +
        "beta|beta2|besselI|besselK|" +
        "numberOfColumns|numberOfRows|" +
//      String functions
        "selected|selected\\$|numberOfSelected|variableExists|"+
        "index|rindex|startsWith|endsWith|"+
        "index_regex|rindex_regex|replace_regex\\$|"+
        "length|extractWord\\$|extractLine\\$|extractNumber|" +
        "left\\$|right\\$|mid\\$|replace\\$|" +
        "date\\$|fixed\\$|percent\\$|" +
//      Array functions
        "zero#|linear#|randomUniform#|randomInteger#|randomGauss#|" +
//      Pause functions
        "beginPause|endPause|" +
//      Demo functions
        "demoShow|demoWindowTitle|demoInput|demoWaitForInput|" +
        "demoClicked|demoClickedIn|demoX|demoY|" +
        "demoKeyPressed|demoKey\\$|" +
        "demoExtraControlKeyPressed|demoShiftKeyPressed|"+
        "demoCommandKeyPressed|demoOptionKeyPressed|" +
//      File functions
        "environment\\$|chooseReadFile\\$|" +
        "chooseDirectory\\$|createDirectory|fileReadable|deleteFile|" +
        "selectObject|removeObject|plusObject|minusObject|" +
        "runScript|exitScript|" +
//      sendpraat functions
        "beginSendPraat|endSendPraat|" +
//      Other
        "objectsAreIdentical"
    );

    var objectTypes = (
        "Activation|AffineTransform|AmplitudeTier|Art|Artword|Autosegment|"  +
        "BarkFilter|CCA|Categories|Cepstrum|Cepstrumc|ChebyshevSeries|"      +
        "ClassificationTable|Cochleagram|Collection|Configuration|"          +
        "Confusion|ContingencyTable|Corpus|Correlation|Covariance|"          +
        "CrossCorrelationTable|CrossCorrelationTables|DTW|Diagonalizer|"     +
        "Discriminant|Dissimilarity|Distance|Distributions|DurationTier|"    +
        "EEG|ERP|ERPTier|Eigen|Excitation|Excitations|ExperimentMFC|FFNet|"  +
        "FeatureWeights|Formant|FormantFilter|FormantGrid|FormantPoint|"     +
        "FormantTier|GaussianMixture|HMM|HMM_Observation|"                   +
        "HMM_ObservationSequence|HMM_State|HMM_StateSequence|Harmonicity|"   +
        "ISpline|Index|Intensity|IntensityTier|IntervalTier|KNN|KlattGrid|"  +
        "KlattTable|LFCC|LPC|Label|LegendreSeries|LinearRegression|"         +
        "LogisticRegression|LongSound|Ltas|MFCC|MSpline|ManPages|"           +
        "Manipulation|Matrix|MelFilter|MixingMatrix|Movie|Network|"          +
        "OTGrammar|OTHistory|OTMulti|PCA|PairDistribution|ParamCurve|"       +
        "Pattern|Permutation|Pitch|PitchTier|PointProcess|Polygon|"          +
        "Polynomial|Procrustes|RealPoint|RealTier|ResultsMFC|Roots|SPINET|"  +
        "SSCP|SVD|Salience|ScalarProduct|Similarity|SimpleString|"           +
        "SortedSetOfString|Sound|Speaker|Spectrogram|Spectrum|SpectrumTier|" +
        "SpeechSynthesizer|SpellingChecker|Strings|StringsIndex|Table|"      +
        "TableOfReal|TextGrid|TextInterval|TextPoint|TextTier|Tier|"         +
        "Transition|VocalTract|Weight|WordList"
    );

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = {
        "start" : [
            {
            // Interpolated strings
                token : "string.interpolated",
                regex : /'((?:[a-z][a-zA-Z0-9_]*)(?:\$|#|:[0-9]+)?)'/
            }, {
            // stopwatch
                token : ["text", "text", "keyword.operator", "text", "keyword"],
                regex : /(^\s*)(?:([a-z][a-zA-Z0-9_]*\$?\s+)(=)(\s+))?(stopwatch)/
            }, {
            // Directives which introduce unquoted strings
                token : ["text", "keyword", "text", "string"],
                regex : /(^\s*)(print(?:line|tab)?|echo|exit|pause|send(?:praat|socket)|include|execute|system(?:_nocheck)?)(\s+)(.*)/
            }, {
            // Directives with no arguments
                token : ["text", "keyword"],
                regex : "(^\\s*)(" + directives + ")$"
            }, {
            // Operators
                token : ["text", "keyword.operator", "text"],
                regex : /(\s+)((?:\+|-|\/|\*|<|>)=?|==?|!=|%|\^|\||and|or|not)(\s+)/
            }, {
            // Commands
                token : ["text", "text", "keyword.operator", "text", "keyword", "text", "keyword"],
                regex : /(^\s*)(?:([a-z][a-zA-Z0-9_]*\$?\s+)(=)(\s+))?(?:((?:no)?warn|(?:unix_)?nocheck|noprogress)(\s+))?((?:[A-Z][^.:"]+)(?:$|(?:\.{3}|:)))/
            }, {
            // Demo commands
                token : ["text", "keyword", "text", "keyword"],
                regex : /(^\s*)(?:(demo)?(\s+))((?:[A-Z][^.:"]+)(?:$|(?:\.{3}|:)))/
            }, {
            // Font-sizing commands
                token : ["text", "keyword", "text", "keyword"],
                regex : /^(\s*)(?:(demo)(\s+))?(10|12|14|16|24)$/
            }, {
            // do-style command calls
                token : ["text", "support.function", "text"],
                regex : /(\s*)(do\$?)(\s*:\s*|\s*\(\s*)/
            }, {
            // Object types
                token : "entity.name.type",
                regex : "(" + objectTypes + ")"
            }, {
            // Predefined variables
                token : "variable.language",
                regex : "(" + predefinedVariables + ")"
            }, {
            // Functions
                token : ["support.function", "text"],
                regex : "((?:" + functions + ")\\$?)(\\s*(?::|\\())"
            }, {
            // For-loop declarations
                token : "keyword",
                regex : /(\bfor\b)/,
                next : "for"
            }, {
            // Generic keywords
                token : "keyword",
                regex : "(\\b(?:" + keywords + ")\\b)"
            }, {
            // Generic strings
                token : "string",
                regex : /"[^"]*"/
            }, {
            // Multiline quoted strings
                token : "string",
                regex : /"[^"]*$/,
                next : "brokenstring"
            }, {
            // Form declarations
                token : ["text", "keyword", "text", "entity.name.section"],
                regex : /(^\s*)(\bform\b)(\s+)(.*)/,
                next : "form"
            }, {
            // Numeric constants
                token : "constant.numeric",
                regex : /\b[+-]?\d+(?:(?:\.\d*)?(?:[eE][+-]?\d+)?)?\b/
            }, {
            // Procedure declarations
                token : ["keyword", "text", "entity.name.function"],
                regex : /(procedure)(\s+)(\S+)/
            }, {
            // New-style procedure calls
                token : ["entity.name.function", "text"],
                regex : /(@\S+)(:|\s*\()/
            }, {
            // Old-style procedure calls
                token : ["text", "keyword", "text", "entity.name.function"],
                regex : /(^\s*)(call)(\s+)(\S+)/
            }, {
            // Comments
                token : "comment",
                regex : /(^\s*#|;).*$/
            }, {
                token : "text",
                regex : /\s+/
            }
        ],
        "form" : [
            {
                token : ["keyword", "text", "constant.numeric"],
                regex : /((?:optionmenu|choice)\s+)(\S+:\s+)([0-9]+)/
            }, {
                token : ["keyword", "constant.numeric"],
                regex : /((?:option|button)\s+)([+-]?\d+(?:(?:\.\d*)?(?:[eE][+-]?\d+)?)?\b)/
            }, {
                token : ["keyword", "string"],
                regex : /((?:option|button)\s+)(.*)/
            }, {
                token : ["keyword", "text", "string"],
                regex : /((?:sentence|text)\s+)(\S+\s*)(.*)/
            }, {
                token : ["keyword", "text", "string", "invalid.illegal"],
                regex : /(word\s+)(\S+\s*)(\S+)?(\s.*)?/
            }, {
                token : ["keyword", "text", "constant.language"],
                regex : /(boolean\s+)(\S+\s*)(0|1|"?(?:yes|no)"?)/
            }, {
                token : ["keyword", "text", "constant.numeric"],
                regex : /((?:real|natural|positive|integer)\s+)(\S+\s*)([+-]?\d+(?:(?:\.\d*)?(?:[eE][+-]?\d+)?)?\b)/
            }, {
                token : ["keyword", "string"],
                regex : /(comment\s+)(.*)/
            }, {
                token : "keyword",
                regex : 'endform',
                next : "start"
            }
        ],
        "for" : [
            {
                token : ["keyword", "text", "constant.numeric", "text"],
                regex : /(from|to)(\s+)([+-]?\d+(?:(?:\.\d*)?(?:[eE][+-]?\d+)?)?)(\s*)/
            }, {
                token : ["keyword", "text"],
                regex : /(from|to)(\s+\S+\s*)/
            }, {
                token : "text",
                regex : /$/,
                next : "start"
            }
        ],
        "brokenstring" : [
            {
                token : ["text", "string"],
                regex : /(\s*\.{3})([^"]*)/
            }, {
                token : "string",
                regex : /"/,
                next : "start"
            }
        ],
    };
};

oop.inherits(PraatHighlightRules, TextHighlightRules);

exports.PraatHighlightRules = PraatHighlightRules;
});
