/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {clickCreate, getFixture} from "@web/../tests/helpers/utils";
let serverData;
let target;

QUnit.module("Website Backend Test", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: {string: "Foo", type: "char"},
                        bar: {string: "Bar", type: "boolean"},
                    },
                    records: [
                        {id: 1, bar: true, foo: "yop"},
                        {id: 2, bar: true, foo: "blip"},
                        {id: 3, bar: true, foo: "gnap"},
                        {id: 4, bar: false, foo: "blip"},
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.test("Website kanban view", async function (assert) {
        assert.expect(1);
        await makeView({
            type: "kanban",
            resModel: "foo",
            serverData,
            arch: `
                <kanban js_class="website_pages_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });
        assert.containsOnce(document.body, ".o_kanban_view");
    });

    QUnit.test("Website Create Object", async function (assert) {
        assert.expect(1);
        
        await makeView({
            type: "form",
            resModel: "foo",
            serverData,
            arch: `
                <form js_class="website_new_content_form">
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="context">{'create_action': 'website_sale.product_product_action_add'}</field>
                </form>`,
        });
        assert.containsOnce(document.body, ".o_form_view");
    });
});
