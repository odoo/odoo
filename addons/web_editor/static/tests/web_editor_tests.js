odoo.define('web_editor.web_editor_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var core = require('web.core');
var web_editor = require('web_editor.editor');

var _t = core._t;

QUnit.module('web_editor', {
    beforeEach: function() {
        this.data = {
            'mass.mailing': {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    body: {string: "Message Body", type: "html"},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    body: "<div class='field_body'>yep</div>",
                }],
                onchanges: {},
            },
        };
    }
});

QUnit.test('field html widget', function (assert) {
    var done = assert.async();
    assert.expect(3);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html" style="height: 100px"/>' +
            '</form>',
        res_id: 1,
    });

    assert.strictEqual(form.$('.field_body').text(), 'yep',
        "should have rendered a div with correct content in readonly");
    assert.strictEqual(form.$('div[name=body]').attr('style'), 'height: 100px',
        "should have applied the style correctly");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('.note-editable').html(), '<div class="field_body">yep</div>',
            "should have rendered the field correctly in edit");

    // summernote invokes handlers after a setTimeout, so we must wait as well
    // before destroying the widget (otherwise we'll have a crash later on)
    setTimeout(function () {
        form.destroy();
        done();
    }, 0);
});

QUnit.test('field html widget (with options inline-style)', function (assert) {
    var done = assert.async();
    assert.expect(3);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html" style="height: 100px" options="{\'style-inline\': true}"/>' +
            '</form>',
        res_id: 1,
    });

    assert.strictEqual(form.$('iframe').length, 1,
        "should have rendered an iframe without crashing in readonly");
    assert.strictEqual(form.$('div[name=body]').attr('style'), 'height: 100px',
        "should have applied the style correctly");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('.note-editable').html(), '<div class="field_body">yep</div>',
            "should have rendered the field correctly in edit");

    // summernote invokes handlers after a setTimeout, so we must wait as well
    // before destroying the widget (otherwise we'll have a crash later on)
    setTimeout(function () {
        form.destroy();
        done();
    }, 0);
});

QUnit.test('field html translatable', function (assert) {
    assert.expect(3);

    var multiLang = _t.database.multi_lang;
    _t.database.multi_lang = true;

    this.data['mass.mailing'].fields.body.translate = true;

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html"/>' +
            '</form>',
        res_id: 1,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_button' && args.method === 'translate_fields') {
                assert.deepEqual(args.args, ['mass.mailing',1,'body',{}], "should call 'call_button' route");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('.oe_form_field_html_text .o_field_translate').length, 0,
        "should not have a translate button in readonly mode");

    form.$buttons.find('.o_form_button_edit').click();
    var $button = form.$('.oe_form_field_html_text .o_field_translate');
    assert.strictEqual($button.length, 1, "should have a translate button");
    $button.click();

    form.destroy();
    _t.database.multi_lang = multiLang;
});

QUnit.test('field html_frame widget', function (assert) {
    assert.expect(6);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html_frame" options="{\'editor_url\': \'/logo\'}"/>' +
            '</form>',
        res_id: 1,
        session: {user_context: {lang: "en_us"}},
        mockRPC: function (route) {
            if (_.str.startsWith(route, '/logo')) {
                // those tests will be executed twice, once in readonly and once in edit
                assert.ok(route.search('model=mass.mailing') > 0,
                    "the route should specify the correct model");
                assert.ok(route.search('res_id=1') > 0,
                    "the route should specify the correct id");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.destroy();
});

QUnit.test('field htmlsimple does not crash when commitChanges is called in mode=readonly', function (assert) {
    assert.expect(1);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<header>' +
                    '<button name="some_method" class="s" string="Do it" type="object"/>' +
                '</header>' +
                '<sheet>' +
                    '<field name="body"/>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        intercepts: {
            execute_action: function () {
                assert.step('execute_action');
            }
        },
    });

    form.$('button:contains(Do it)').click();
    form.destroy();
});

QUnit.test('html_frame does not crash when saving in readonly', function (assert) {
    // The 'Save' action may be triggered even in readonly (e.g. when clicking
    // on a button in the form view)
    assert.expect(2);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="body" widget="html_frame" options="{\'editor_url\': \'/logo\'}"/>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        mockRPC: function (route, args) {
            if (args.method) {
                assert.step(args.method);
            }
            if (_.str.startsWith(route, '/logo')) {
                // manually call the callback to simulate that the iframe has
                // been loaded (note: just the content, not the editor)
                window.odoo[$.deparam(route).callback + '_content'].call();
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    form.saveRecord(); // before the fix done in this commit, it crashed here
    
    assert.verifySteps(['read']);

    form.destroy();
});

QUnit.test('html_frame does not crash when saving in edit mode (editor not loaded)', function (assert) {
    // The 'Save' action may be triggered when saving in edit mode very fast
    // so that the editor may be not loaded, even though the content is!
    assert.expect(2);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="body" widget="html_frame" options="{\'editor_url\': \'/logo\'}"/>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        mockRPC: function (route, args) {
            if (args.method) {
                assert.step(args.method);
            }
            if (_.str.startsWith(route, '/logo')) {
                // manually call the callback to simulate that the iframe has
                // been partially loaded (just the content, not the editor)
                window.odoo[$.deparam(route).callback + '_content']();
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    form.$buttons.find('.o_form_button_edit').click();
    form.$('input').val('trululu').trigger('input');
    form.$buttons.find('.o_form_button_save').click(); // crash without editor fully loaded

    assert.verifySteps(['read']);

    form.destroy();
});

QUnit.test('html_frame saving in edit mode (editor and content fully loaded)', function (assert) {
    var done = assert.async();
    assert.expect(4);

    var editorBar = new web_editor.Class();
    var loadDeferred = $.Deferred();
    var writeDeferred = $.Deferred();

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="body" widget="html_frame" options="{\'editor_url\': \'/logo\'}"/>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        mockRPC: function (route, args) {
            if (args.method) {
                assert.step(args.method);
                if (args.method === 'write') {
                    writeDeferred.resolve();    
                }
            }
            if (_.str.startsWith(route, '/logo')) {
                // manually call the callback to simulate that the iframe has
                // been fully loaded (content + editor)
                var callback = $.deparam(route).callback;
                return loadDeferred.then(function () {
                    var contentCallback = window.odoo[callback + '_content'];
                    var editorCallback = window.odoo[callback + '_editor'];
                    if (editorCallback && contentCallback) {
                        contentCallback();
                        editorCallback(editorBar);
                    }
                });
            }
            return this._super.apply(this, arguments);
        },
    });

    form.$buttons.find('.o_form_button_edit').click();
    form.$('input').val('trululu').trigger('input');
    form.$buttons.find('.o_form_button_save').click();

    loadDeferred.resolve(); // simulate late loading of html frame

    assert.strictEqual(form.$('.o_field_char').val(), 'trululu',
        "should have saved the char field text");

    writeDeferred.then( function () { // html_frame is async with write
        assert.verifySteps(['read', 'write']);
        form.destroy();
        done();
    });

});

});
