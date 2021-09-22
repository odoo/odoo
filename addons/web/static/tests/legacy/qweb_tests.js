odoo.define('web.qweb_tests', function (require) {
"use strict";

const {Markup} = require('web.utils');

var qwebPath = '/web/static/lib/qweb/';
const {hushConsole} = require('@web/../tests/helpers/utils');

function trim(s) {
    return s.replace(/(^\s+|\s+$)/g, '');
}

/**
 * Promise-based wrapper for QWeb2.Engine#add_template
 *
 * The base version is callbacks-based which is a bit shit, and it also has
 * variable asynchronicity: it'll be async if passed a URL but not if passed
 * either a Document or an XML string.
 *
 * Either way this converts the `(error, doc)` callback to a `Promise<Document>`
 * as in it literally returns the parsed DOM Document.
 *
 * @param qweb the qweb instance to load the template into
 * @param {String|Document} template qweb template (Document, template file, or template URL)
 */
function add_template(qweb, template) {
    return new Promise(function (resolve, reject) {
        qweb.add_template(template, (error, doc) => error ? reject(error) : resolve(doc));
    });
}

/**
 * Loads the template file, and executes all the test template in a
 * qunit module $title
 *
 * @param assert QUnit assertion module
 * @param {String|Document} templateFile template container to load
 * @param {Object} [context] additional rendering context
 */
async function loadTest(assert, templateFile, context) {
    const qweb = new window.QWeb2.Engine();
    const doc = await add_template(qweb, qwebPath + templateFile);

    assert.expect(doc.querySelectorAll('result').length);

    const templates = qweb.templates;
    for (const template in templates) {
        if (!templates.hasOwnProperty(template)) {
            continue;
        }
        // ignore templates whose name starts with _, they're
        // helpers/internal
        if (/^_/.test(template)) {
            continue;
        }

        const results = doc.querySelector(`result#${template}`).textContent.replace(/\r/g, '');
        const params = doc.querySelector(`params#${template}`) || {textContent: 'null'};
        const args = {...JSON.parse(params.textContent), ...context};

        try {
            assert.equal(trim(qweb.render(template, args)), trim(results), template);
        } catch (error) {
            assert.notOk(error.stack || error, `Rendering error for ${template} (in ${templateFile} with context ${JSON.stringify(args)}).`);
        }
    }
}

const table = [
    {name: 'Output', file: 'qweb-test-output.xml'},
    {name: 'Context-setting', file: 'qweb-test-set.xml'},
    {name: 'Conditionals', file: 'qweb-test-conditionals.xml'},
    {name: 'Attributes manipulation', file: 'qweb-test-attributes.xml'},
    {name: 'Templates calling (to the faraway pages)', file: 'qweb-test-call.xml', context: {True: true}},
    {name: 'Foreach', file: 'qweb-test-foreach.xml'},
    {
        name: 'Global', file: 'qweb-test-global.xml',
        // test uses python syntax
        context: {bool: (v) => !!v ? 'True' : 'False'},
        fixture: {
            before() {
                this.WORD_REPLACEMENT = window.QWeb2.WORD_REPLACEMENT;
                window.QWeb2.WORD_REPLACEMENT = _.extend(
                    {not: '!', None: 'undefined'},
                    this.WORD_REPLACEMENT
                )
            },
            after() {
                window.QWeb2.WORD_REPLACEMENT = this.WORD_REPLACEMENT;
            }
        }
    },
    {name: 'Template Inheritance', file: 'qweb-test-extend.xml'},
];
QUnit.module('QWeb', {
        beforeEach() {
            this.oldConsole = window.console;
            window.console = hushConsole;
        },
        afterEach() {window.console = this.oldConsole;}
}, () => {
    for(const {name, file, context, fixture} of table) {
        QUnit.test(name, async assert => {
            // fake expect to avoid qunit being a pain in the ass, loadTest will
            // update it
            assert.expect(1);
            if (fixture && 'before' in fixture) { await fixture.before(); }
            try {
                await loadTest(assert, file, context);
            } finally {
                if (fixture && 'after' in fixture) { await fixture.after(); }
            }
        });
    }
    QUnit.test('escape', assert => {
        // not strictly about qweb...
        assert.expect(8);
        assert.equal(_.escape('a'), 'a');
        assert.equal(_.escape('<a>'), '&lt;a&gt;');
        assert.equal(_.escape({[_.escapeMethod]() { return 'a'; }}), 'a');
        assert.equal(_.escape({[_.escapeMethod]() { return '<a>'; }}), '<a>');
        assert.equal(_.escape(Markup('a')), 'a');
        assert.equal(_.escape(Markup('<a>')), '<a>');
        assert.equal(_.escape(Markup`a`), 'a');
        assert.equal(_.escape(Markup`<a>`), '<a>');
    });
    QUnit.module('t-out', {}, () => {
        QUnit.test("basics", async assert => {
            assert.expect(5);
            const qweb = new QWeb2.Engine;
            await add_template(qweb, `<templates>
                <t t-name="t-out"><p><t t-out="value"/></p></t>
            </templates>`);

            assert.equal(
                qweb.render('t-out', {value: '<i>test</i>'}),
                '<p>&lt;i&gt;test&lt;/i&gt;</p>',
                "regular t-out should just escape the contents"
            );
            assert.equal(
                qweb.render('t-out', {value: Markup('<i>test</i>')}),
                '<p><i>test</i></p>',
                "Markup contents should not be escaped"
            );
            assert.equal(
                qweb.render('t-out', {value: Markup`<i>test ${1}</i>`}),
                '<p><i>test 1</i></p>',
                "markup template string should not be escaped"
            );
            const teststr = '<i>test</i>';
            assert.equal(
                qweb.render('t-out', {value: Markup`<b>${teststr}</b>`}),
                '<p><b>&lt;i&gt;test&lt;/i&gt;</b></p>',
                "the markup template should not be escaped but what it uses should be"
            );
            const testMarkup = Markup(teststr);
            assert.equal(
                qweb.render('t-out', {value: Markup`<b>${testMarkup}</b>`}),
                '<p><b><i>test</i></b></p>',
                "markupception"
            );
        });
        QUnit.test("Set", async assert => {
            assert.expect(4);
            const qweb = new QWeb2.Engine;
            await add_template(qweb, `<templates>
<t t-name="litval">
    <t t-set="x" t-value="'&lt;a/&gt;'"/>
    <x><t t-out="x"/></x>
</t>
<t t-name="body">
    <t t-set="x"><a/></t>
    <x><t t-out="x"/></x>
</t>
<t t-name="value">
    <t t-set="x" t-value="val"/>
    <x><t t-out="x"/></x>
</t>
<t t-name="bodyout">
    <t t-set="x"><t t-out="val"/></t>
    <x><t t-out="x"/></x>
</t>
            </templates>`);

            assert.equal(trim(qweb.render('litval')), '<x>&lt;a/&gt;</x>');
            assert.equal(trim(qweb.render('body')), '<x><a></a></x>');
            assert.equal(trim(qweb.render('value', {val: '<a/>'})), '<x>&lt;a/&gt;</x>');
            assert.equal(trim(qweb.render('bodyout', {val: '<a/>'})), '<x>&lt;a/&gt;</x>');
        });
    })
});
});
