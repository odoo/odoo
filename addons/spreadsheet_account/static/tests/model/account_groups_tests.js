/** @odoo-module */

import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { getCellValue } from "@spreadsheet/../tests/utils/getters";
import { getAccountingData } from "../accounting_test_data";

let serverData;

function beforeEach() {
    serverData = getAccountingData();
}

QUnit.module("spreadsheet_account > account groups", { beforeEach }, () => {
    QUnit.test("get no account", async (assert) => {
        const model = await createModelWithDataSource({ serverData });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("test")`);
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), "");
    });

    QUnit.test("get one account", async (assert) => {
        const model = await createModelWithDataSource({ serverData });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income_other")`);
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), "100105");
    });

    QUnit.test("get multiple accounts", async (assert) => {
        const model = await createModelWithDataSource({ serverData });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), "100104,200104");
    });
});
