odoo.define('website.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require("web.test_utils");
var MockServer = require('web.MockServer');

var createView = testUtils.createView;

MockServer.include({
    /**
     * @override
     * @private
     * @param {Object} args
     */
    _mockSearchReadController: function (args) {
        if (args.model === 'website') {
            return {
                length: 2,
                records: [
                    {'id': 1, 'name': 'My Website'},
                    {'id': 2, 'name': 'My Website 2'},
                ],
            };
        } else {
            return this._super.apply(this, arguments);
        }
    },
});

QUnit.module('website', {
    before: function () {
        this.data = {
            blog_post: {
                fields: {
                    website_published: {string: "Available on the Website", type: "boolean"},
                },
                records: [{
                    id: 1,
                    website_published: false,
                }, {
                    id: 2,
                    website_published: true,
                }]
            }
        };
    },
}, function () {
    QUnit.test("widget website button: display false value", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'blog_post',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<field name="website_published" widget="website_redirect_button"/>' +
                        '</div>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        var selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_stat_text';
        assert.containsN(form, selector, 1, "there should be one text displayed");
        selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_button_icon.fa-globe.text-danger';
        assert.containsOnce(form, selector, "there should be one icon in red");
        form.destroy();
    });
    QUnit.test("widget website button: display true value", async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'blog_post',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<field name="website_published" widget="website_redirect_button"/>' +
                        '</div>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });
        var selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_stat_text';
        assert.containsN(form, selector, 1, "should be one text displayed");
        selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_button_icon.fa-globe.text-success';
        assert.containsOnce(form, selector, "there should be one text in green");
        form.destroy();
    });
});

});
