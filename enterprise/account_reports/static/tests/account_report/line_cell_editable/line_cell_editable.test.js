import { expect, test } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, makeMockEnv, defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

import { AccountReportLineCellEditable } from "@account_reports/components/account_report/line_cell_editable/line_cell_editable";

// Due to dependency with mail module, we have to define their models for our tests.
defineModels(mailModels);

test("can unformat a value when focus and format when blur", async () => {
    const env = await makeMockEnv({
        controller: {},
    });
    await mountWithCleanup(AccountReportLineCellEditable, {
        env,
        props: {
            cell: {
                name: "5,702.22",
                no_format: 5702.22,
                edit_popup_data: {},
            },
            line: {},
        },
    });

    expect(".o_input").toHaveValue("5,702.22");
    await click(".o_input");
    await animationFrame();
    expect(".o_input").toHaveValue("5702.22");
    await press("Enter");
    await animationFrame();
    expect(".o_input").toHaveValue("5,702.22");
});
