import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { getCellValue } from "@spreadsheet/../tests/helpers/getters";
import {
    getAccountingData,
    defineSpreadsheetAccountModels,
} from "@spreadsheet_account/../tests/accounting_test_data";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetAccountModels();

const serverData = getAccountingData();

test("get no account", async () => {
    const model = await createModelWithDataSource({ serverData });
    setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("test")`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("");
});

test("get one account", async () => {
    const model = await createModelWithDataSource({ serverData });
    setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income_other")`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("100105");
});

test("get multiple accounts", async () => {
    const model = await createModelWithDataSource({ serverData });
    setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("100104,200104");
});
