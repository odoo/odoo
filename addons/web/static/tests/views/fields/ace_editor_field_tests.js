/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    click,
    getFixture,
    nextTick,
    triggerEvent,
    triggerEvents,
} from "@web/../tests/helpers/utils";
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

    QUnit.test(
        "leaving an untouched record with an unset ace field should not write",
        async (assert) => {
            serverData.models.partner.records.forEach((rec) => {
                rec.foo = false;
            });
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                resIds: [1, 2],
                serverData,
                arch: /* xml */ `
                <form>
                    <field name="foo" widget="ace" />
                </form>`,
                mockRPC(route, args) {
                    if (args.method) {
                        assert.step(`${args.method}: ${JSON.stringify(args.args)}`);
                    }
                },
            });

            assert.verifySteps(["get_views: []", 'read: [[1],["foo","display_name"]]']);
            await pagerNext(target);
            assert.verifySteps(['read: [[2],["foo","display_name"]]']);
        }
    );

    QUnit.test("AceEditorField only trigger onchanges when blurred", async (assert) => {
        serverData.models.partner.onchanges = {
            foo: (obj) => {},
        };

        serverData.models.partner.records.forEach((rec) => {
            rec.foo = false;
        });
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            resIds: [1, 2],
            serverData,
            arch: `<form>
                <field name="display_name" />
                <field name="foo" widget="code" />
            </form>`,
            mockRPC(route, args) {
                if (args.method) {
                    assert.step(`${args.method}: ${JSON.stringify(args.args)}`);
                }
            },
        });

        assert.verifySteps(["get_views: []", 'read: [[1],["display_name","foo"]]']);
        const textArea = target.querySelector(".ace_editor textarea");
        await click(textArea);
        textArea.focus();
        textArea.value = "a";
        await triggerEvent(textArea, null, "input", {});
        await triggerEvents(textArea, null, ["blur"]);
        assert.verifySteps([
            'onchange: [[1],{"id":1,"display_name":false,"foo":"a"},"foo",{"display_name":"","foo":"1"}]',
        ]);
        await click(target, ".o_form_button_save");
        assert.verifySteps(['write: [[1],{"foo":"a"}]', 'read: [[1],["display_name","foo"]]']);
    });
});
