/** @odoo-module **/

import { registry } from "@web/core/registry";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("redirect_field", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                appointment: {
                    fields: {
                        is_published: {
                            string: "Is published",
                            type: "boolean",
                            searchable: true,
                            trim: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            is_published: true,
                        },
                    ],
                },
                blog_post: {
                    fields: {
                        is_published: {
                            string: "Is published",
                            type: "boolean",
                            searchable: true,
                            trim: true,
                        }
                    },
                    records: [
                        {
                            id: 1,
                            is_published: true,
                        },
                        {
                            id: 2,
                            is_published: false,
                        }
                    ]
                }
            },
        };

        setupViewRegistries();
    });

    QUnit.test("redirect field in form view is green if value=true", async function (assert) {
        await makeView({
            type: "form",
            resModel: "appointment",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <field name="is_published" widget="website_redirect_button" />
                        </div>
                    </sheet>
                </form>`,
        });
        assert.containsOnce(target, ".oe_stat_button .o_button_icon.text-success")
    });

    QUnit.test("clicking on redirect field works", async function (assert) {
        registry.category("services").add(
            "action",
            {
                start() {
                    return {
                        doActionButton(data) {
                            assert.step(data.type);
                            assert.step(data.name);
                        },
                    };
                },
            },
            { force: true }
        );

        await makeView({
            type: "form",
            resModel: "appointment",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <field name="is_published" widget="website_redirect_button" />
                        </div>
                    </sheet>
                </form>`,
        });
        await click(target, ".oe_stat_button");

        assert.verifySteps(['object', 'open_website_url']);
    });
    QUnit.test("redirect field in form view is green if value=true", async function (assert) {
        await makeView({
            type: "form",
            resModel: "blog_post",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <field name="is_published" widget="website_redirect_button" />
                        </div>
                    </sheet>
                </form>`,
        });
        assert.containsOnce(target, ".oe_stat_button .o_button_icon.text-success", "redirect field is green");
    });
    QUnit.test("redirect field in form view is red if value=false", async function (assert) {
        await makeView({
            type: "form",
            resModel: "blog_post",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <field name="is_published" widget="website_redirect_button" />
                        </div>
                    </sheet>
                </form>`,
        });
        assert.containsOnce(target, ".oe_stat_button .o_button_icon.text-danger", "redirect field is red");
    });
});
