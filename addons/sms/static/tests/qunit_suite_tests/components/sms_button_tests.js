/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { getFixture } from "@web/../tests/helpers/utils";


QUnit.module('fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    message: {string: "message", type: "text"},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    mobile: {string: "mobile", type: "text"},
                },
                records: [{
                    id: 1,
                    message: "",
                    foo: 'yop',
                    mobile: "+32494444444",
                }, {
                    id: 2,
                    message: "",
                    foo: 'bayou',
                }]
            },
            visitor: {
                fields: {
                    mobile: {string: "mobile", type: "text"},
                },
                records: [{
                    id: 1,
                    mobile: "+32494444444",
                }]
            },
        };
        setupViewRegistries();
        this.target = getFixture();
    }
}, function () {

    QUnit.module('SmsButton');

    QUnit.test('Sms button in form view', async function (assert) {
        await makeView({
            type: "form",
            resModel: "visitor",
            resId: 1,
            serverData: { models: this.data },
            arch: /* xml */ `
                <form>
                    <sheet>
                        <field name="mobile" widget="phone"/>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(this.target.querySelector('.o_field_phone'), ".o_field_phone_sms", "the button is present");
    });

    QUnit.test('Sms button with option enable_sms set as False', async function (assert) {
        await makeView({
            type: "form",
            resModel: "visitor",
            resId: 1,
            serverData: { models: this.data },
            mode: "readonly",
            arch: /* xml */ `
                <form>
                    <sheet>
                        <field name="mobile" widget="phone" options="{'enable_sms': false}"/>
                    </sheet>
                </form>`,
        });

        assert.containsNone(this.target.querySelector('.o_field_phone'), ".o_field_phone_sms", "the button is not present");
    });

});
