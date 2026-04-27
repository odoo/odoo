import {
    contains,
    mountView,
    patchWithCleanup,
    toggleActionMenu,
} from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { session } from "@web/session";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";

describe.current.tags("desktop");
defineSpreadsheetModels();

async function openListActionMenu() {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list>
                <field name="foo"/>
            </list>`,
        actionMenus: {},
    });
    await contains("thead .o_list_record_selector input").click();
    await toggleActionMenu();
}

test("Insert in Spreadsheet is available when the user have permission", async function () {
    await openListActionMenu();
    expect(".o-dropdown--menu .o_menu_item:has(.oi-view-list)").toHaveCount(1);
});

test("Insert in Spreadsheet is unavailable when the user lacks permission", async function () {
    patchWithCleanup(session, { can_insert_in_spreadsheet: false });
    await openListActionMenu();
    expect(".o-dropdown--menu .o_menu_item:has(.oi-view-list)").toHaveCount(0);
});
