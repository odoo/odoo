/** @odoo-module **/

import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";

let serverData;
let target;

QUnit.module("Debug > Profiling QWeb", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        const qweb = JSON.stringify([
            {
                exec_context: [],
                results: {
                    archs: {
                        1: `<t name="Test1" t-name="test">
                    <t t-call-assets="web.assets_tests"/>
                </t>`,
                    },
                    data: [
                        {
                            delay: 0.1,
                            directive: 't-call-assets="web.assets_tests"',
                            query: 9,
                            view_id: 1,
                            xpath: "/t/t",
                        },
                    ],
                },
                stack: [],
                start: 42,
            },
        ]);
        serverData = {
            models: {
                partner: {
                    fields: {
                        qweb: {
                            string: "QWeb",
                            type: "text",
                        },
                    },
                    records: [{ qweb }],
                },
                "ir.ui.view": {
                    fields: {
                        model: { type: "char" },
                        name: { type: "char" },
                        type: { type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "formView",
                            model: "partner",
                            type: "form",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
    });

    QUnit.test("profiling qweb view field renders delay and query", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
            <form>
                <field name="qweb" widget="profiling_qweb_view" />
            </form>`,
        });

        assert.containsN(target, "[name='qweb'] .ace_gutter .ace_gutter-cell", 3);
        assert.containsN(target, "[name='qweb'] .ace_gutter .ace_gutter-cell .o_info", 1);
        const infoEl = target.querySelector("[name='qweb'] .ace_gutter .ace_gutter-cell .o_info");
        assert.strictEqual(infoEl.querySelector(".o_delay").textContent, "0.1");
        assert.strictEqual(infoEl.querySelector(".o_query").textContent, "9");

        const header = target.querySelector("[name='qweb'] .o_select_view_profiling");
        assert.strictEqual(header.querySelector(".o_delay").textContent, "0.1 ms");
        assert.strictEqual(header.querySelector(".o_query").textContent, "9 query");
    });
});
