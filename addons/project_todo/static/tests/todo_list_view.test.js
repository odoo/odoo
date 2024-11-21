import { describe, expect, test } from "@odoo/hoot";
import { check, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { mountView, contains } from "@web/../tests/web_test_helpers";

import { defineTodoModels } from "./todo_test_helpers";

describe.current.tags("desktop");
defineTodoModels();

const listViewArch = `
    <list js_class="todo_list">
        <field name="name"></field>
    </list>`;

test("Check that todo_list view is restricted to archive, unarchive, duplicate and delete menu actions", async () => {
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: listViewArch,
        actionMenus: {},
    });

    const [firstRow] = queryAll(".o_data_row");
    await check(".o_list_record_selector input", { root: firstRow });
    await animationFrame();
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts`.o_menu_item`).toEqual([
        "Export",
        "Archive",
        "Unarchive",
        "Duplicate",
        "Delete",
    ]);
});
