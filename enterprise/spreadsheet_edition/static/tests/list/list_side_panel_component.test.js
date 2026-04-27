import { expect, getFixture, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { contains } from "@web/../tests/web_test_helpers";

defineSpreadsheetModels();

async function openListSidePanel(listId) {
    await contains(".o-topbar-menu[data-id='data']").click();
    await contains(`.o-menu-item[data-name='item_list_${listId}']`).click();
}

test("can remove an invalid sorting field", async () => {
    const orderBy = [{ name: "an_invalid_field", asc: true }];
    const { model } = await createSpreadsheetWithList({
        model: "partner",
        orderBy,
    });
    await mountSpreadsheet(model);
    const [listId] = model.getters.getListIds();
    expect(model.getters.getListDefinition(listId).orderBy).toEqual(orderBy);
    await openListSidePanel(listId);
    expect(".o_sorting_rule_column .fa-exclamation-triangle").toHaveCount(1);
    await contains(".o_sorting_rule_column .fa-times").click();
    expect(model.getters.getListDefinition(listId).orderBy).toEqual([]);
});

test("can display a list with invalid fields", async () => {
    const columns = ["name"];
    const badColumns = ["name", "an_invalid_field"];
    const { model } = await createSpreadsheetWithList({
        model: "partner",
        columns,
    });
    const listId = model.getters.getListIds()[0];
    const listDefinition = model.getters.getListModelDefinition(listId);
    model.dispatch("UPDATE_ODOO_LIST", {
        listId,
        list: {
            ...listDefinition,
            columns: badColumns,
        },
    });
    await mountSpreadsheet(model);
    expect(model.getters.getListDefinition(listId).columns).toEqual(columns);
    await openListSidePanel(listId);
    const columnNames = getFixture().querySelectorAll(".columns-list>div");
    expect([...columnNames].map((node) => node.textContent)).toEqual(["name"]);
});
