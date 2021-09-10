/** @odoo-module **/

import { click, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    setupControlPanelServiceRegistry,
    toggleFavoriteMenu,
    toggleMenu,
} from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");
let serverData;

QUnit.module("Dashboard", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                'partner': {
                    fields: {
                        user_id: { string: "User ID", type: "integer", store: true },
                        category: { string: "Category", type: "selection", selection: [["a", "A"], ["b", "B"]], store: true },

                    },
                    records: [
                        { id: 1, user_id: 10, category: "a" },
                        { id: 2, user_id: 20, category: "b" },
                        { id: 3, user_id: 30, category: "a" },
                    ],
                },
            },
            views: {
                "partner,false,graph": /* xml */ `
                    <graph>
                        <field name="category" />
                    </graph>`,
                "partner,false,search": /* xml */ `
                    <search>
                        <filter name="filterA" string="Me" domain="[('user_id', '=', uid)]" />
                        <filter name="groupByA" string="Category" context="{ 'group_by': 'category' }" />
                    </search>`,
            }
        }
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module("Add to board");

    QUnit.test("Save correct domain and context to dashboard", async (assert) => {
        assert.expect(3);

        patchWithCleanup(session, { uid: 30 });

        const view = await makeView({
            serverData,
            async mockRPC(route, kwargs) {
                if (route === "/board/add_to_dashboard") {
                    assert.deepEqual(kwargs, {
                        action_id: 666,
                        context_to_save: {
                            dashboard_merge_domains_contexts: false,
                            graph_groupbys: ["category"],
                            graph_measure: "__count",
                            graph_mode: "bar",
                            group_by: ["category"],
                            orderedBy: undefined,
                        },
                        domain: `[("user_id", "=", uid)]`,
                        name: "Graphy McGraphface",
                        view_mode: "graph",
                    });
                    return true;
                }
            },
            resModel: "partner",
            type: "graph",
            views: [[false, "search"]],
            action: {
                id: 666,
                type: "ir.actions.act_window",
            },
            displayName: "Graphy McGraphface",
            context: {
                search_default_filterA: true,
                search_default_groupByA: true,
            },
        });

        assert.deepEqual(
            view.env.searchModel.domain,
            [["user_id", "=", 30]],
            "The search model domain should be correctly evaluated"
        );

        await toggleFavoriteMenu(view);
        await toggleMenu(view, "Add to my dashboard");

        const boardMenu = view.el.querySelector(".o_add_to_board .o_dropdown_menu");

        assert.strictEqual(
            boardMenu.querySelector("input").value,
            "Graphy McGraphface",
            "The input should show the action display name by default"
        );

        await click(boardMenu, ".btn-primary");
    });
});
