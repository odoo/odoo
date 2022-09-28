/** @odoo-module **/

import FormView from 'web.FormView';
import testUtils from "web.test_utils";

var createView = testUtils.createView;

QUnit.module('mrp', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    state: {
                        string: "State",
                        type: "selection",
                        selection: [['waiting', 'Waiting'], ['chilling', 'Chilling']],
                    },
                    duration: {string: "Duration", type: "float"},
                },
                records: [{
                    id: 1,
                    state: 'waiting',
                    duration: 6000,
                }],
                onchanges: {},
            },
        };
    },
}, function () {

    QUnit.test("embed_viewer rendering in form view", async function (assert) {
        assert.expect(8);
        var data = {
            foo: {
                fields: { char_url: { string: "URL", type: "char" } },
                records: [{ id: 1 }]
            },
        };

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: data,
            arch:
                '<form>' +
                '<field name="char_url" widget="embed_viewer"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route) {
                if (route === ('http://example.com')) {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.isNotVisible(form.$('iframe.o_embed_iframe'), "there should be an invisible iframe readonly mode");
        assert.strictEqual(_.has(form.$('iframe.o_embed_iframe')[0].attributes, "src"), false,
            "src attribute is not set if there are no values");
        await testUtils.form.clickEdit(form);
        assert.isNotVisible(form.$('iframe.o_embed_iframe'), "there should be an invisible iframe in edit mode");
        await testUtils.fields.editAndTrigger(form.$('.o_field_char'), 'http://example.com', ['input', 'change', 'focusout']);
        assert.strictEqual(form.$('iframe.o_embed_iframe').attr('data-src'), 'http://example.com',
            "src should updated on the iframe");
        assert.isVisible(form.$('iframe.o_embed_iframe'), "there should be a visible iframe in edit mode");
        await testUtils.form.clickSave(form);
        assert.isVisible(form.$('iframe.o_embed_iframe'), "there should be a visible iframe in readonly mode");
        assert.strictEqual(form.$('iframe.o_embed_iframe').attr('data-src'), 'http://example.com',
            "should have updated src in readonly mode");

        // In readonly mode, we are not displaying the URL, only iframe will be there.
        assert.strictEqual(form.$('.iframe.o_embed_iframe').siblings().length, 0,
            "there shouldn't be any siblings of iframe in readonly mode");

        form.destroy();
    });
});
