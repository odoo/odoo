/** @odoo-module */

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

function getColumn(groupIndex = 0, ignoreFolded = false) {
    let selector = ".o_kanban_group";
    if (ignoreFolded) {
        selector += ":not(.o_column_folded)";
    }
    return target.querySelectorAll(selector)[groupIndex];
}

async function toggleColumnActions(columnIndex) {
    const group = getColumn(columnIndex);
    await click(group, ".o_kanban_config .dropdown-toggle");
    const buttons = group.querySelectorAll(".o_kanban_config .dropdown-menu .dropdown-item");
    return (buttonText) => {
        const re = new RegExp(`\\b${buttonText}\\b`, "i");
        const button = [...buttons].find((b) => re.test(b.innerText));
        return click(button);
    };
}

let target;
let serverData;

QUnit.module("BaseAutomation", {}, function () {
    QUnit.module("BaseAutomationKanbanHeader", (hooks) => {
        hooks.beforeEach(() => {
            target = getFixture();
            serverData = {
                models: {
                    partner: {
                        fields: {
                            foo: { string: "Foo", type: "char" },
                            bar: { string: "Bar", type: "boolean" },
                        },
                        records: [
                            {
                                id: 1,
                                bar: true,
                                foo: "yop",
                            },
                            {
                                id: 2,
                                bar: true,
                                foo: "blip",
                            },
                            {
                                id: 3,
                                bar: true,
                                foo: "gnap",
                            },
                            {
                                id: 4,
                                bar: false,
                                foo: "blip",
                            },
                        ],
                    },
                },
            };
            setupViewRegistries();
        });

        QUnit.test("basic grouped rendering with automations", async (assert) => {
            const actionService = {
                start() {
                    return {
                        doAction: (action, options) => {
                            assert.step(action);
                            assert.deepEqual(options, {
                                additionalContext: {
                                    active_test: false,
                                    search_default_model_id: 42,
                                    default_model_id: 42,
                                    default_trigger: "on_create_or_write",
                                },
                            });
                        },
                    };
                },
            };
            registry.category("services").add("action", actionService, { force: true });
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData: serverData,
                arch: `
                    <kanban class="o_kanban_test">
                        <field name="bar" />
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="foo" />
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
                groupBy: ["bar"],
                mockRPC: (route, { args, kwargs }) => {
                    if (route === "/web/dataset/call_kw/ir.model/search") {
                        assert.deepEqual(args, [[["model", "=", "partner"]]]);
                        assert.strictEqual(kwargs.limit, 1);
                        return [42]; // model id
                    }
                },
            });
            assert.hasClass(target.querySelector(".o_kanban_view"), "o_kanban_test");
            assert.hasClass(target.querySelector(".o_kanban_renderer"), "o_kanban_grouped");
            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsOnce(target, ".o_kanban_group:first-child .o_kanban_record");
            assert.containsN(target, ".o_kanban_group:nth-child(2) .o_kanban_record", 3);

            await toggleColumnActions(0);

            // check available actions in kanban header's config dropdown
            assert.containsOnce(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_kanban_toggle_fold"
            );
            assert.containsOnce(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_automations"
            );
            assert.containsNone(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_edit"
            );
            assert.containsNone(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_delete"
            );
            assert.containsNone(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_archive_records"
            );
            assert.containsNone(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_unarchive_records"
            );
            assert.verifySteps([]);
            await click(
                target,
                ".o_kanban_header:first-child .o_kanban_config .o_column_automations"
            );
            assert.verifySteps(["base_automation.base_automation_act"]);
        });
    });
});
