import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { defineSpreadsheetActions, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";

import "@hr_spreadsheet_dashboard/spreadsheet/odoo_views_data_source_patch";

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

function createDataSource(resModel, domain) {
    return new OdooViewsDataSource(
        { odooDataProvider: {} },
        {
            metaData: { resModel },
            searchParams: { domain, context: {} },
        }
    );
}

test("hr.employee replaces company_id 'in' leaf with allowed_company_ids", () => {
    patchWithCleanup(user, {
        context: { ...user.context, allowed_company_ids: [1, 2] },
    });

    const dataSource = createDataSource("hr.employee", [["company_id", "in", [99]]]);
    expect(dataSource.getComputedDomain()).toEqual([["company_id", "in", [1, 2]]]);
});

test("hr.employee dynamically reflects changes to allowed_company_ids", () => {
    patchWithCleanup(user, {
        context: { ...user.context, allowed_company_ids: [1] },
    });

    const dataSource = createDataSource("hr.employee", [["company_id", "in", [99]]]);
    expect(dataSource.getComputedDomain()).toEqual([["company_id", "in", [1]]]);

    user.context.allowed_company_ids = [2, 3];
    expect(dataSource.getComputedDomain()).toEqual([["company_id", "in", [2, 3]]]);
});

test("hr.employee does not modify company_id leaf with other operators", () => {
    patchWithCleanup(user, {
        context: { ...user.context, allowed_company_ids: [1, 2] },
    });

    const childOfDataSource = createDataSource("hr.employee", [["company_id", "child_of", [1]]]);
    expect(childOfDataSource.getComputedDomain()).toEqual([["company_id", "child_of", [1]]]);

    const equalDataSource = createDataSource("hr.employee", [["company_id", "=", 1]]);
    expect(equalDataSource.getComputedDomain()).toEqual([["company_id", "=", 1]]);
});

test("non-hr.employee models do not replace company_id 'in' leaf", () => {
    patchWithCleanup(user, {
        context: { ...user.context, allowed_company_ids: [1, 2] },
    });

    const partnerDataSource = createDataSource("res.partner", [["company_id", "in", [99]]]);
    expect(partnerDataSource.getComputedDomain()).toEqual([["company_id", "in", [99]]]);
});

test("hr.employee preserves other domain leaves in compound domain", () => {
    patchWithCleanup(user, {
        context: { ...user.context, allowed_company_ids: [1, 2] },
    });

    const dataSource = createDataSource("hr.employee", [
        "&",
        ["active", "=", true],
        ["company_id", "in", [99]],
    ]);
    expect(dataSource.getComputedDomain()).toEqual([
        "&",
        ["active", "=", true],
        ["company_id", "in", [1, 2]],
    ]);
});

test("hr.employee list in spreadsheet model updates computed domain", async () => {
    patchWithCleanup(user, {
        context: { ...user.context, allowed_company_ids: [1, 2] },
    });

    const model = await createModelWithDataSource();
    model.dispatch("INSERT_ODOO_LIST", {
        sheetId: model.getters.getActiveSheetId(),
        definition: {
            metaData: {
                resModel: "hr.employee",
                columns: ["name"],
            },
            searchParams: {
                domain: [["company_id", "in", [99]]],
                context: {},
                orderBy: [],
            },
            name: "Employees",
        },
        linesNumber: 5,
        columns: [{ name: "name", type: "char" }],
        id: "1",
        col: 0,
        row: 0,
    });

    const listDataSource = model.getters.getListDataSource("1");
    expect(listDataSource.getComputedDomain()).toEqual([["company_id", "in", [1, 2]]]);

    user.context.allowed_company_ids = [3, 4];
    expect(listDataSource.getComputedDomain()).toEqual([["company_id", "in", [3, 4]]]);
});
