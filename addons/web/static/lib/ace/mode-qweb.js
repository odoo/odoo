define("ace/mode/qweb_highlight_rules", ["require", "exports", "module", "ace/lib/oop", "ace/mode/xml_highlight_rules"], function (require, exports, module) {
    "use strict";

    var oop = require("../lib/oop");
    var XmlHighlightRules = require("./xml_highlight_rules").XmlHighlightRules;

    var QWebHighlightRules = function (options) {
        XmlHighlightRules.call(this);
        const xmlRules = this.$rules;

        const attributes_display_custom = [];
        if (options?.readonlyAttributes) {
            const attrRegx = options.readonlyAttributes.join("|");
            attributes_display_custom.push({
                regex: `(${attrRegx})(=)(\\s*)(")([^"]*)(")`,
                token: ["entity.other.attribute-name.xml.odoo_attr_readonly", "keyword.operator.attribute-equals.xml.odoo_attr_readonly", "text.odoo_attr_readonly", "string.attribute-value.xml.start.odoo_attr_readonly", "string.attribute-value.xml.code.odoo_attr_readonly", "string.attribute-value.xml.end.odoo_attr_readonly"],
            })
        }

        const tagRegex = xmlRules.attributes[0].regex;

        this.$rules = Object.assign({},
            xmlRules,
            {
                attributes: [{
                    include: "attributes_display_custom",
                }, {
                    include: "attributes_odoo",
                }, {
                    include: "attributes_qweb",
                }, {
                    include: "attributes_groups",
                }, {
                    include: "attributes_sample",
                }],

                attributes_display_custom,

                attributes_odoo: [{
                    token: ["entity.other.attribute-name.xml.odoo", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml.code", "string.attribute-value.xml.end"],
                    regex: '(domain|attrs|options)(=)(\\s*)(")([^"]*)(")',
                }, {
                    token: ["entity.other.attribute-name.xml.odoo", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml.code", "string.attribute-value.xml.end"],
                    regex: "(domain|attrs|options)(=)(\\s*)(')([^']*)(')",
                }],

                attributes_qweb: [{
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml", "string.attribute-value.xml.end"],
                    regex: '(t-name|t-call-assets|t-js|t-css)(=)(\\s*)(")([^"]*)(")',
                }, {
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml", "string.attribute-value.xml.end"],
                    regex: "(t-name|t-call-assets|t-js|t-css)(=)(\\s*)(')([^']*)(')",
                }, {
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml", "string.attribute-value.xml", "string.attribute-value.xml.code", "string.attribute-value.xml", "string.attribute-value.xml", "string.attribute-value.xml.end"],
                    regex: '(t-call|t-attf-(?:' + tagRegex + '))(=)(\\s*)(")([^"#{]*)(?:([#{]\\{)([^"}]+)(\\}[}]?))?([^"]*)(")',
                }, {
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml", "string.attribute-value.xml", "string.attribute-value.xml.code", "string.attribute-value.xml", "string.attribute-value.xml", "string.attribute-value.xml.end"],
                    regex: "(t-call|t-attf-(?:" + tagRegex + "))(=)(\\s*)(')([^'#{]*)(?:([#{]\\{)([^'}]+)(\\}[}]?))?([^']*)(')",
                }, {
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml.code", "string.attribute-value.xml.end"],
                    regex: '(t-(?:' + tagRegex + '))(=)(\\s*)(")([^"]*)(")',
                }, {
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml.code", "string.attribute-value.xml.end"],
                    regex: "(t-(?:" + tagRegex + "))(=)(\\s*)(')([^']*)(')",
                }],

                attributes_groups: [{
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml", "string.attribute-value.xml.end"],
                    regex: '(groups)(=)(\\s*)(")([\\s\\na-zA-Z0-9.,_-]*)(")',
                }, {
                    token: ["entity.other.attribute-name.xml.qweb", "keyword.operator.attribute-equals.xml", "text", "string.attribute-value.xml.start", "string.attribute-value.xml", "string.attribute-value.xml.end"],
                    regex: "(groups)(=)(\\s*)(')((?:[\\s\\na-zA-Z0-9.,_-]*)*)(')",
                }],

                attributes_sample: [{
                    token: "entity.other.attribute-name.xml",
                    regex: tagRegex,
                }, {
                    token: "keyword.operator.attribute-equals.xml",
                    regex: "=",
                }, {
                    include: "tag_whitespace",
                }, {
                    include: "attribute_value",
                }],

                tag: [{
                    token: ["meta.tag.punctuation.tag-open.xml", "meta.tag.punctuation.end-tag-open.xml", "meta.tag.tag-name.xml"],
                    regex: "(?:(<)|(</))((?:" + tagRegex + ":)?" + tagRegex + ")",
                    next: [{
                            include: "attributes",
                        }, {
                            token: ["meta.tag.punctuation.end-tag-close.xml", "meta.tag.punctuation.tag-close.xml"],
                            regex: "(/>)|(>)",
                            next: "start",
                        },
                    ],
                }],
            },
        );

        if (this.constructor === QWebHighlightRules) {
            this.normalizeRules();
        }
    };

    oop.inherits(QWebHighlightRules, XmlHighlightRules);

    exports.QWebHighlightRules = QWebHighlightRules;
});

define("ace/mode/qweb",["require","exports","module","ace/lib/oop","ace/lib/lang","ace/mode/text","ace/mode/qweb_highlight_rules","ace/mode/behaviour/xml","ace/mode/folding/xml","ace/worker/worker_client"], function(require, exports, module) {
    "use strict";

    var oop = require("../lib/oop");
    var lang = require("../lib/lang");
    var TextMode = require("./text").Mode;
    var TokenIterator = require("ace/token_iterator").TokenIterator;
    var QWebHighlightRules = require("./qweb_highlight_rules").QWebHighlightRules;
    var XmlBehaviour = require("./behaviour/xml").XmlBehaviour;
    var XmlFoldMode = require("./folding/xml").FoldMode;
    var WorkerClient = require("../worker/worker_client").WorkerClient;
    const AceRange = require("ace/range").Range;

    function* getTokensInRange(session, range) {
        const tokenIterator = new TokenIterator(session, range.start.row, range.start.column);
        while (true) {
            const token = tokenIterator.getCurrentToken();
            if (!token) {
                return;
            }
            const tRange = tokenIterator.getCurrentTokenRange();
            if (!intersects(range, tRange, false)) {
                return;
            }
            if (!intersects(range, tRange)) {
                yield { ...token, tokenRange: tRange, edge: true };
            } else {
                yield { ...token, tokenRange: tRange };
            }
            tokenIterator.stepForward();
        }
    }

    // See issue https://github.com/ajaxorg/ace/issues/5877
    function intersects(r1, r2, exludeEnd=true) {
        if (exludeEnd) {
            r1 = new AceRange(r1.start.row, r1.start.column, r1.end.row, r1.end.column - 1)
            r2 = new AceRange(r2.start.row, r2.start.column, r2.end.row, r2.end.column - 1)
        }
        return r1.intersects(r2)
    }

    function getOrphansReadonlyAttributesFromTokens(tokens) {
        const readOnlys = [];
        let currentTagRo = null;
        for (const token of tokens) {
            if (!token || token.edge) {
                continue;
            }
            if (token.type === "meta.tag.punctuation.tag-open.xml") {
                if (currentTagRo) {
                    readOnlys.push(currentTagRo);
                }
                currentTagRo = [];
            }
            if (token.type === "meta.tag.punctuation.tag-close.xml") {
                currentTagRo = null;
            }
            if (token.type?.includes(".odoo_attr_readonly")) {
                (currentTagRo || readOnlys).push(token);
            }
        }
        if (currentTagRo) {
            readOnlys.push(currentTagRo);
        }
        return readOnlys.flat();
    }

    var Mode = function(options) {
        this.HighlightRules = QWebHighlightRules;
        this.$behaviour = new XmlBehaviour();

        const highlightRulesConfig = {
            ...(this.$highlightRuleConfig || {}),
            ...(options?.highlightRulesConfig || {}),
        };
        if (highlightRulesConfig.readonlyAttributes?.length) {
            this.$highlightRuleConfig = {...highlightRulesConfig };
            this.$behaviour.add("readonly_attr", "insertion", (state, action, editor, session, text) => {
                const range = editor.getSelectionRange();
                const tokensInRange = [...getTokensInRange(session, range)];

                // do not insert anything if we are writing over an orphan readonly attribute
                if (getOrphansReadonlyAttributesFromTokens(tokensInRange).length) {
                    editor.selection.setSelectionRange(new AceRange(range.start.row, range.start.column, range.start.row, range.start.column));
                    return { text: "" }
                }

                // Make sure we insert a space before a readonly attribute
                const lastToken = tokensInRange.at(-1);
                if (lastToken?.edge && !text.endsWith(" ") && lastToken?.type?.includes(".odoo_attr_readonly")) {
                    return { text: text + " ", selection: [text.length, text.length] };
                }
            });

            this.$behaviour.add("readonly_attr", "deletion", (state, action, editor, session, range) => {
                // Cancels a deletion if we are deleting orphans readonly attributes
                const tokensInRange = [...getTokensInRange(session, range)];
                if (getOrphansReadonlyAttributesFromTokens(tokensInRange).length) {
                    return new AceRange(range.start.row, range.start.column, range.start.row, range.start.column);
                }
            });
        }

        this.foldingRules = new XmlFoldMode();
    };

    oop.inherits(Mode, TextMode);

    (function() {

        this.voidElements = lang.arrayToMap([]);

        this.blockComment = {start: "<!--", end: "-->"};

        this.createWorker = function(session) {
            var worker = new WorkerClient(["ace"], "ace/mode/xml_worker", "Worker");
            worker.attachToDocument(session.getDocument());

            worker.on("error", function(e) {
                session.setAnnotations(e.data);
            });

            worker.on("terminate", function() {
                session.clearAnnotations();
            });

            return worker;
        };

        this.$id = "ace/mode/qweb";
    }).call(Mode.prototype);

    exports.Mode = Mode;
});
