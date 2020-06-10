odoo.define('website.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require("web.test_utils");

var createView = testUtils.createView;

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
    QUnit.test("website_redirect_button: display false value", async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'blog_post',
            data: this.data,
            arch: `<form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <field name="website_published" widget="website_redirect_button"/>
                        </div>
                    </sheet>
                </form>`,
            res_id: 1,
        });
        let selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_stat_text';
        assert.containsN(form, selector, 1, "there should be one text displayed");
        selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_button_icon.fa-globe.text-danger';
        assert.containsOnce(form, selector, "there should be one icon in red");
        form.destroy();
    });
    QUnit.test("website_redirect_button: display true value", async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'blog_post',
            data: this.data,
            arch: `<form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <field name="website_published" widget="website_redirect_button"/>
                        </div>
                    </sheet>
                </form>`,
            res_id: 2,
        });
        let selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_stat_text';
        assert.containsN(form, selector, 1, "should be one text displayed");
        selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_button_icon.fa-globe.text-success';
        assert.containsOnce(form, selector, "there should be one text in green");
        form.destroy();
    });
    QUnit.test("website_publish_button: display true value", async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'blog_post',
            data: this.data,
            debug: true,
            arch: `<form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button name="website_published" type="object" class="oe_stat_button" icon="fa-globe">
                                <field name="website_published" widget="website_publish_button"/>
                            </button>
                        </div>
                    </sheet>
                </form>`,
            res_id: 2,
        });
        const selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_stat_text';
        assert.containsN(form, `${selector}`, 2, 'should be two span displayed');
        assert.containsOnce(form, `${selector}:first.text-success`, 'first span text should be green');
        form.destroy();
    });
    QUnit.test("website_publish_button: display false value", async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'blog_post',
            data: this.data,
            debug: true,
            arch: `<form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button name="website_published" type="object" class="oe_stat_button" icon="fa-globe">
                                <field name="website_published" widget="website_publish_button"/>
                            </button>
                        </div>
                    </sheet>
                </form>`,
            res_id: 1,
        });
        const selector = '.oe_button_box .oe_stat_button[name="website_published"] .o_stat_text';
        assert.containsN(form, `${selector}`, 2, 'should be two span displayed');
        assert.containsOnce(form, `${selector}:first.text-danger`, 'first span text should be green');
        form.destroy();
    });
});

});
