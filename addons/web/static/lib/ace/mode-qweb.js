define("ace/mode/qweb_highlight_rules", ["require", "exports", "module", "ace/lib/oop", "ace/mode/xml_highlight_rules"], function (require, exports, module) {
    "use strict";

    var oop = require("../lib/oop");
    var XmlHighlightRules = require("./xml_highlight_rules").XmlHighlightRules;

    var QWebHighlightRules = function () {
        XmlHighlightRules.call(this);
        const xmlRules = this.$rules;

        const tagRegex = xmlRules.attributes[0].regex;

        this.$rules = Object.assign({},
            xmlRules,
            {
                attributes: [{
                    include: "attributes_odoo",
                }, {
                    include: "attributes_qweb",
                }, {
                    include: "attributes_groups",
                }, {
                    include: "attributes_sample",
                }],

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
    var QWebHighlightRules = require("./qweb_highlight_rules").QWebHighlightRules;
    var XmlBehaviour = require("./behaviour/xml").XmlBehaviour;
    var XmlFoldMode = require("./folding/xml").FoldMode;
    var WorkerClient = require("../worker/worker_client").WorkerClient;

    var Mode = function() {
       this.HighlightRules = QWebHighlightRules;
       this.$behaviour = new XmlBehaviour();
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

        this.$id = "ace/mode/xml";
    }).call(Mode.prototype);

    exports.Mode = Mode;
});
