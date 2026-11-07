/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

let serverData, target;

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                project: {
                    fields: {
                        foo: { string: "Foo", type: "boolean" },
                    },
                    records: [
                        {
                            id: 1,
                            foo: true,
                        },
                        {
                            id: 2,
                            foo: false,
                        },
                    ],
                },
            },
            views: {
                "project,false,list": '<list><field name="foo"/></list>',
                "project,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name='kanban-box'>
                            <div class='oe_kanban_card'>
                                <field name='foo' />
                            </div>
                        </t>
                    </templates>
                </kanban>
                `,
                "project,false,search": "<search></search>",
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("Window Actions");

    QUnit.test("execute a window action with mobile_view_mode", async (assert) => {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            xml_id: "project.action",
            name: "Project Action",
            res_model: "project",
            type: "ir.actions.act_window",
            view_mode: "list,kanban",
            mobile_view_mode: "list",
            views: [
                [false, "kanban"],
                [false, "list"],
            ],
        });
        assert.containsOnce(target, ".o_list_view");
    });
});
