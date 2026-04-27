import { mailModels } from "@mail/../tests/mail_test_helpers";
import { before, describe, expect, test } from "@odoo/hoot";
import { registries } from "@odoo/o-spreadsheet";
import { defineModels } from "@web/../tests/web_test_helpers";

import { addSpreadsheetFieldSyncExtensionWithCleanUp } from "../src/bundle/field_sync/field_sync_extension_hook";
import { addFieldSync, createSaleOrderSpreadsheetModel } from "./helpers/commands";
import { defineSpreadsheetSaleModels } from "./helpers/data";
import { getFieldSync } from "./helpers/getters";

import { selectCell } from "@spreadsheet/../tests/helpers/commands";
import { doMenuAction, getActionMenu } from "@spreadsheet/../tests/helpers/ui";

const { cellMenuRegistry } = registries;

describe.current.tags("headless");

defineModels(mailModels);
defineSpreadsheetSaleModels();

before(() => {
    addSpreadsheetFieldSyncExtensionWithCleanUp();
});

test("add a field sync at the selected cell", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    const env = {
        ...model.config.custom.env,
        model,
        openSidePanel(tag) {
            expect.step(tag);
        },
    };
    selectCell(model, "B2");
    await doMenuAction(cellMenuRegistry, ["add_field_sync"], env);
    const fieldSync = getFieldSync(model, "B2");
    expect(fieldSync).toEqual({
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList: 0,
        fieldName: "product_uom_qty",
    });
    expect.verifySteps(["FieldSyncSidePanel"]);
});

test("delete a field sync at the selected cell", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    addFieldSync(model, "B2", "product_uom_qty", 0);
    const env = {
        ...model.config.custom.env,
        model,
    };
    selectCell(model, "B2");
    await doMenuAction(cellMenuRegistry, ["delete_field_syncs"], env);
    expect(getFieldSync(model, "B2")).toBe(undefined);
});

test("delete is not visible if there's nothing to delete", async () => {
    const model = await createSaleOrderSpreadsheetModel();
    const env = {
        ...model.config.custom.env,
        model,
    };
    selectCell(model, "B2");
    const menu = getActionMenu(cellMenuRegistry, ["delete_field_syncs"], env);
    expect(await menu.isVisible(env)).toBe(false);
});
