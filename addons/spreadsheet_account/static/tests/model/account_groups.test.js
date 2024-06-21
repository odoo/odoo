/** @odoo-module */

import { setCellContent } from "@spreadsheet/../tests/legacy/utils/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/legacy/utils/model";
import { getCellValue } from "@spreadsheet/../tests/legacy/utils/getters";
import { getAccountingData } from "@spreadsheet_account/../tests/legacy/accounting_test_data";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

let serverData;

function beforeEach() {
    serverData = getAccountingData();
}

QUnit.module("spreadsheet_account > account groups", { beforeEach }, () => {
    QUnit.test("get no account", async (assert) => {
        const model = await createModelWithDataSource({ serverData });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("test")`);
        await waitForDataLoaded(model);
        assert.equal(getCellValue(model, "A1"), "");
    });

    QUnit.test("get one account", async (assert) => {
        const model = await createModelWithDataSource({ serverData });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income_other")`);
        await waitForDataLoaded(model);
        assert.equal(getCellValue(model, "A1"), "100105");
    });

    QUnit.test("get multiple accounts", async (assert) => {
        const model = await createModelWithDataSource({ serverData });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
        await waitForDataLoaded(model);
        assert.equal(getCellValue(model, "A1"), "100104,200104");
    });
});
