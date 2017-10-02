odoo.define('qweb.tests', function () {
'use strict';

function trim(s) {
    return s.replace(/(^\s+|\s+$)/g, '');
}

/**
 * Generates a QUnit.module hook object loading the specified test file
 * (from /web/static/lib/qweb) and setting ``this.qweb`` (the qweb
 * instance for this module) and ``this.doc`` (the loaded XML file).
 *
 * Note that test files mix template elements <t t-name>, params elements
 * <params> and result elements <result>. A result and an optional params
 * object are linked to the corresponding template via the ``id``
 * attribute (result and params have the template name as id).
 */
function hooks(testfile) {
    var template = '/web/static/lib/qweb/' + testfile;
    return {
        before: function () {
            var self = this;
            this.qweb = new QWeb2.Engine();
            var p = $.Deferred();
            this.qweb.add_template(template, function (_, doc) {
                self.doc = doc;
                p.resolve(doc);
            });
            return p.promise();
        }
    }
}
// can't get generative QUnit.test (e.g. QUnit.test in a for(;;)
// or Array#forEach() loop) to work, so each test file has a single test,
// that seems to work
function runtest() {
    QUnit.test('', function (assert) {
    var templates = this.qweb.templates;
    assert.expect(_.reduce(templates, function (acc, _, k) {
        return acc + (/^_/.test(k) ? 0 : 1);
    }, 0));
    for (var template in templates) {
        if (!templates.hasOwnProperty(template)) { continue; }
        // ignore templates whose name starts with _, they're
        // helpers/internal
        if (/^_/.test(template)) { continue; }

        var params = this.doc.querySelector('params#' + template);
        var args = params ? JSON.parse(params.textContent) : {};

        var results = this.doc.querySelector('result#' + template);
        assert.equal(
            trim(this.qweb.render(template, args)),
            trim(results.textContent),
            template);
        }
    });
}

var TEMPLATES = [
    ["Output", 'qweb-test-output.xml'],
    ["Context-setting", 'qweb-test-set.xml'],
    ["Conditionals", 'qweb-test-conditionals.xml'],
    ["Attributes manipulation", 'qweb-test-attributes.xml'],
    ["Template calling (to the faraway pages)", 'qweb-test-call.xml'],
    ["Foreach", 'qweb-test-foreach.xml'],
    ["Global", 'qweb-test-global.xml'],
    ['Template inheritance', 'qweb-test-extend.xml']
];

QUnit.module('qweb', {}, function () {
    TEMPLATES.forEach(function (it) {
        QUnit.module(it[0], hooks(it[1]), runtest);
    })
});

});
