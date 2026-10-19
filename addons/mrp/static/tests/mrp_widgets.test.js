import { SampleServer } from "@web/model/sample_server";
import { describe, expect, test } from "@odoo/hoot";

import { openFormView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineMrpModels } from "@mrp/../tests/mrp_test_helpers";
import {
    fields,
    mountView,
    onRpc,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { ResFake } from "./mock_server/mock_models/res_fake";

describe.current.tags("desktop");
defineMrpModels();

test("ensure the rendering is based on hours, minutes and seconds", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ duration: 150.5 });
    await start();
    await openFormView("res.fake", fakeId);
    expect(".o_field_mrp_timer").toHaveText("2h 30m 30s");
});

test("timer field in list view: don't crash when leaving sample mode", async () => {
    ResFake._fields.state = fields.Selection({
        selection: [["blocked", "Blocked"],
            ["ready", "To Do"],
            ["progress", "In Progress"],
            ["done", "Done"],
            ["cancel", "Cancelled"],
        ],
    });
    const pyEnv = await startServer();
    pyEnv["res.fake"].create({ duration: 12.5, state: "progress" });

    patchWithCleanup(SampleServer.prototype, {
        _generateFieldValue(resModel, fieldName) {
            // force "progress" value for "state" field to trigger rpc in useRecordObserver callback
            if (resModel === "res.fake" && fieldName === "state") {
                return "progress";
            }
            return super._generateFieldValue(...arguments);
        }
    });

    onRpc("mrp.workorder", "get_duration", ({ args }) => {
        expect.step(args);
        return 42;
    });

    await mountView({
        resModel: "res.fake",
        type: "list",
        arch: `
            <list sample="1">
                <field name="state" column_invisible="1"/>
                <field name="duration" widget="mrp_timer"/>
            </list>`,
        searchViewArch: `
            <search>
                <filter name="empty" domain="[('id', '&lt;', 0)]"/>
            </search>`,
        context: { search_default_empty: true },
    });
    expect(".o_content").toHaveClass("o_view_sample_data");
    expect(".o_data_row").toHaveCount(10);

    // remove the filter to leave sample mode
    await toggleSearchBarMenu();
    await toggleMenuItem("empty");

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_data_row").toHaveCount(1);
    expect.verifySteps([[1]]);
});
