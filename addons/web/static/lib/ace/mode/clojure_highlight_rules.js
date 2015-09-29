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
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;



var ClojureHighlightRules = function() {

    var builtinFunctions = (
        '* *1 *2 *3 *agent* *allow-unresolved-vars* *assert* *clojure-version* ' +
        '*command-line-args* *compile-files* *compile-path* *e *err* *file* ' +
        '*flush-on-newline* *in* *macro-meta* *math-context* *ns* *out* ' +
        '*print-dup* *print-length* *print-level* *print-meta* *print-readably* ' +
        '*read-eval* *source-path* *use-context-classloader* ' +
        '*warn-on-reflection* + - -> ->> .. / < <= = ' +
        '== > &gt; >= &gt;= accessor aclone ' +
        'add-classpath add-watch agent agent-errors aget alength alias all-ns ' +
        'alter alter-meta! alter-var-root amap ancestors and apply areduce ' +
        'array-map aset aset-boolean aset-byte aset-char aset-double aset-float ' +
        'aset-int aset-long aset-short assert assoc assoc! assoc-in associative? ' +
        'atom await await-for await1 bases bean bigdec bigint binding bit-and ' +
        'bit-and-not bit-clear bit-flip bit-not bit-or bit-set bit-shift-left ' +
        'bit-shift-right bit-test bit-xor boolean boolean-array booleans ' +
        'bound-fn bound-fn* butlast byte byte-array bytes cast char char-array ' +
        'char-escape-string char-name-string char? chars chunk chunk-append ' +
        'chunk-buffer chunk-cons chunk-first chunk-next chunk-rest chunked-seq? ' +
        'class class? clear-agent-errors clojure-version coll? comment commute ' +
        'comp comparator compare compare-and-set! compile complement concat cond ' +
        'condp conj conj! cons constantly construct-proxy contains? count ' +
        'counted? create-ns create-struct cycle dec decimal? declare definline ' +
        'defmacro defmethod defmulti defn defn- defonce defstruct delay delay? ' +
        'deliver deref derive descendants destructure disj disj! dissoc dissoc! ' +
        'distinct distinct? doall doc dorun doseq dosync dotimes doto double ' +
        'double-array doubles drop drop-last drop-while empty empty? ensure ' +
        'enumeration-seq eval even? every? false? ffirst file-seq filter find ' +
        'find-doc find-ns find-var first float float-array float? floats flush ' +
        'fn fn? fnext for force format future future-call future-cancel ' +
        'future-cancelled? future-done? future? gen-class gen-interface gensym ' +
        'get get-in get-method get-proxy-class get-thread-bindings get-validator ' +
        'hash hash-map hash-set identical? identity if-let if-not ifn? import ' +
        'in-ns inc init-proxy instance? int int-array integer? interleave intern ' +
        'interpose into into-array ints io! isa? iterate iterator-seq juxt key ' +
        'keys keyword keyword? last lazy-cat lazy-seq let letfn line-seq list ' +
        'list* list? load load-file load-reader load-string loaded-libs locking ' +
        'long long-array longs loop macroexpand macroexpand-1 make-array ' +
        'make-hierarchy map map? mapcat max max-key memfn memoize merge ' +
        'merge-with meta method-sig methods min min-key mod name namespace neg? ' +
        'newline next nfirst nil? nnext not not-any? not-empty not-every? not= ' +
        'ns ns-aliases ns-imports ns-interns ns-map ns-name ns-publics ' +
        'ns-refers ns-resolve ns-unalias ns-unmap nth nthnext num number? odd? ' +
        'or parents partial partition pcalls peek persistent! pmap pop pop! ' +
        'pop-thread-bindings pos? pr pr-str prefer-method prefers ' +
        'primitives-classnames print print-ctor print-doc print-dup print-method ' +
        'print-namespace-doc print-simple print-special-doc print-str printf ' +
        'println println-str prn prn-str promise proxy proxy-call-with-super ' +
        'proxy-mappings proxy-name proxy-super push-thread-bindings pvalues quot ' +
        'rand rand-int range ratio? rational? rationalize re-find re-groups ' +
        're-matcher re-matches re-pattern re-seq read read-line read-string ' +
        'reduce ref ref-history-count ref-max-history ref-min-history ref-set ' +
        'refer refer-clojure release-pending-sends rem remove remove-method ' +
        'remove-ns remove-watch repeat repeatedly replace replicate require ' +
        'reset! reset-meta! resolve rest resultset-seq reverse reversible? rseq ' +
        'rsubseq second select-keys send send-off seq seq? seque sequence ' +
        'sequential? set set-validator! set? short short-array shorts ' +
        'shutdown-agents slurp some sort sort-by sorted-map sorted-map-by ' +
        'sorted-set sorted-set-by sorted? special-form-anchor special-symbol? ' +
        'split-at split-with str stream? string? struct struct-map subs subseq ' +
        'subvec supers swap! symbol symbol? sync syntax-symbol-anchor take ' +
        'take-last take-nth take-while test the-ns time to-array to-array-2d ' +
        'trampoline transient tree-seq true? type unchecked-add unchecked-dec ' +
        'unchecked-divide unchecked-inc unchecked-multiply unchecked-negate ' +
        'unchecked-remainder unchecked-subtract underive unquote ' +
        'unquote-splicing update-in update-proxy use val vals var-get var-set ' +
        'var? vary-meta vec vector vector? when when-first when-let when-not ' +
        'while with-bindings with-bindings* with-in-str with-loading-context ' +
        'with-local-vars with-meta with-open with-out-str with-precision xml-seq ' +
        'zero? zipmap'
    );

    var keywords = ('throw try var ' +
        'def do fn if let loop monitor-enter monitor-exit new quote recur set!'
    );

    var buildinConstants = ("true false nil");

    var keywordMapper = this.createKeywordMapper({
        "keyword": keywords,
        "constant.language": buildinConstants,
        "support.function": builtinFunctions
    }, "identifier", false, " ");

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = {
        "start" : [
            {
                token : "comment",
                regex : ";.*$"
            }, {
                token : "keyword", //parens
                regex : "[\\(|\\)]"
            }, {
                token : "keyword", //lists
                regex : "[\\'\\(]"
            }, {
                token : "keyword", //vectors
                regex : "[\\[|\\]]"
            }, {
                token : "keyword", //sets and maps
                regex : "[\\{|\\}|\\#\\{|\\#\\}]"
            }, {
                    token : "keyword", // ampersands
                    regex : '[\\&]'
            }, {
                    token : "keyword", // metadata
                    regex : '[\\#\\^\\{]'
            }, {
                    token : "keyword", // anonymous fn syntactic sugar
                    regex : '[\\%]'
            }, {
                    token : "keyword", // deref reader macro
                    regex : '[@]'
            }, {
                token : "constant.numeric", // hex
                regex : "0[xX][0-9a-fA-F]+\\b"
            }, {
                token : "constant.numeric", // float
                regex : "[+-]?\\d+(?:(?:\\.\\d*)?(?:[eE][+-]?\\d+)?)?\\b"
            }, {
                token : "constant.language",
                regex : '[!|\\$|%|&|\\*|\\-\\-|\\-|\\+\\+|\\+||=|!=|<=|>=|<>|<|>|!|&&]'
            }, {
                token : keywordMapper,
                regex : "[a-zA-Z_$][a-zA-Z0-9_$\\-]*\\b"
            }, {
                token : "string", // single line
                regex : '"',
                next: "string"
            }, {
                token : "constant", // symbol
                regex : /:[^()\[\]{}'"\^%`,;\s]+/
            }, {
                token : "string.regexp", //Regular Expressions
                regex : '/#"(?:\\.|(?:\\\")|[^\""\n])*"/g'
            }

        ],
        "string" : [
            {
                token : "constant.language.escape",                
                regex : "\\\\.|\\\\$"
            }, {
                token : "string",                
                regex : '[^"\\\\]+'
            }, {
                token : "string",
                regex : '"',
                next : "start"
            }
        ]
    };
};

oop.inherits(ClojureHighlightRules, TextHighlightRules);

exports.ClojureHighlightRules = ClojureHighlightRules;
});
