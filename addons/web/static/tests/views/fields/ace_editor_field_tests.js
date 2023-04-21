/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getFixture, nextTick, triggerEvents } from "@web/../tests/helpers/utils";
import { pagerNext } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { fakeCookieService } from "@web/../tests/helpers/mock_services";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "text",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                    },
                    records: [
                        { id: 1, foo: `yop` },
                        { id: 2, foo: `blip` },
                    ],
                },
            },
        };

        setupViewRegistries();
        registry.category("services").add("cookie", fakeCookieService);
    });

    QUnit.module("AceEditorField");

    QUnit.test("AceEditorField on text fields works", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" widget="code" />
                </form>`,
        });

        assert.ok("ace" in window, "the ace library should be loaded");
        assert.containsOnce(
            target,
            "div.ace_content",
            "should have rendered something with ace editor"
        );

        assert.ok(target.querySelector(".o_field_code").textContent.includes("yop"));
    });

    QUnit.test("AceEditorField doesn't crash when editing", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="display_name" />
                    <field name="foo" widget="code" />
                </form>`,
        });

        await triggerEvents(target, ".ace-view-editor textarea", ["focus", "click"]);
        assert.hasClass(target.querySelector(".ace-view-editor"), "ace_focus");
    });

    QUnit.test("AceEditorField is updated on value change", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            resIds: [1, 2],
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="foo" widget="code" />
                </form>`,
        });

        assert.ok(target.querySelector(".o_field_code").textContent.includes("yop"));

        await pagerNext(target);
        await nextTick();

        assert.ok(target.querySelector(".o_field_code").textContent.includes("blip"));
    });
});
