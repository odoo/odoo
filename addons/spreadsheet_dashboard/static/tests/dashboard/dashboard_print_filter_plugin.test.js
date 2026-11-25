import { describe, expect, getFixture, test } from "@odoo/hoot";
import { createSpreadsheetDashboard } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { press } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

defineSpreadsheetDashboardModels();

function iframeQuery(selector) {
    return getFixture().querySelector("iframe").contentWindow.document.querySelector(selector);
}

test("Filters are printed on the first page", async () => {
    await createSpreadsheetDashboard();
    await press(["ctrl", "p"]);
    await contains("iframe").click();
    expect("iframe.o-print-preview").toHaveCount(1);
    expect(iframeQuery(".o-title-filter-print-page")).toHaveCount(1);
    expect(iframeQuery(".o-first-page")).toHaveCount(1);
    expect(iframeQuery(".o-first-page h1")).toHaveInnerHTML("Dashboard CRM 1");
    expect(iframeQuery(".o-first-page h3")).toHaveCount(1);
    expect(iframeQuery(".o-ul-filters")).toHaveCount(1);
})
