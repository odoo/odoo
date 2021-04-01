odoo.define('web.qweb_tests', function (require) {
"use strict";

var qwebPath = '/web/static/lib/qweb/';

function trim(s) {
    return s.replace(/(^\s+|\s+$)/g, '');
}

/**
 * Loads the template file, and executes all the test template in a
 * qunit module $title
 */
function loadTest(assert, template, context) {
    var done = assert.async();
    assert.expect(1);

    var qweb = new window.QWeb2.Engine();
    var prom = new Promise(function (resolve, reject) {
        qweb.add_template(qwebPath + template, function (error, doc) {
            if (error) {
                return reject(error);
            }
            resolve({
                qweb: qweb,
                doc: doc
            });
        });
    });

    prom.then(function (r) {
        var qweb = r.qweb;
        var doc = r.doc;
        assert.expect(doc.querySelectorAll('result').length);

        var templates = qweb.templates;
        for (var template in templates) {
            try {
                if (!templates.hasOwnProperty(template)) {
                    continue;
                }
                // ignore templates whose name starts with _, they're
                // helpers/internal
                if (/^_/.test(template)) {
                    continue;
                }

                var params = doc.querySelector('params#' + template);
                var args = params ? JSON.parse(params.textContent) : (context ? _.clone(context) : {});

                var results = doc.querySelector('result#' + template);

                assert.equal(
                    trim(qweb.render(template, args)),
                    trim(results.textContent.replace(new RegExp(String.fromCharCode(13), 'g'), '')),
                    template);
            } catch (error) {
                assert.notOk(error.stack || error, 'Rendering error');
            }
        }
        done();
    });
    return prom;
}

QUnit.module('QWeb', {}, function () {
    QUnit.test('Output', function (assert) {
        loadTest(assert, 'qweb-test-output.xml');
    });
    QUnit.test('Context-setting', function (assert) {
        loadTest(assert, 'qweb-test-set.xml');
    });
    QUnit.test('Conditionals', function (assert) {
        loadTest(assert, 'qweb-test-conditionals.xml');
    });
    QUnit.test('Attributes manipulation', function (assert) {
        loadTest(assert, 'qweb-test-attributes.xml');
    });
    QUnit.test('Template calling (to the faraway pages)', function (assert) {
        loadTest(assert, 'qweb-test-call.xml', {True: true});
    });
    QUnit.test('Foreach', function (assert) {
        loadTest(assert, 'qweb-test-foreach.xml');
    });
    QUnit.test('Global', function (assert) {
        // test use python syntax
        var WORD_REPLACEMENT = window.QWeb2.WORD_REPLACEMENT;
        window.QWeb2.WORD_REPLACEMENT = _.extend({not: '!', None: 'undefined'}, WORD_REPLACEMENT);
        loadTest(assert, 'qweb-test-global.xml', {bool: function (v) { return !!v ? 'True' : 'False';}})
            .then(function () {
                window.QWeb2.WORD_REPLACEMENT = WORD_REPLACEMENT;
            }, function () {
                window.QWeb2.WORD_REPLACEMENT = WORD_REPLACEMENT;
            });
    });
    QUnit.test('Template inheritance', function (assert) {
        loadTest(assert, 'qweb-test-extend.xml');
    });
});
});
