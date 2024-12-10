import {
    contains,
    mailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { ResPartner } from "@mail/../tests/mock_server/mock_models/res_partner";
import { describe, test } from "@odoo/hoot";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("status bar duration field used in form view", async () => {
    class Stage extends models.Model {
        _name = "stage";
        name = fields.Char();
    }
    ResPartner._fields.stage_id = fields.Many2one({ relation: "stage" });
    ResPartner._fields.duration_tracking = fields.Json();
    defineModels({ ...mailModels, ResPartner, Stage });
    const pyEnv = await startServer();
    const stageIds = pyEnv["stage"].create([
        { name: "New" },
        { name: "Qualified" },
        { name: "Proposition" },
        { name: "Won" },
    ]);
    const partnerId = pyEnv["res.partner"].create({
        name: "John Doe",
        stage_id: stageIds[2].id,
        // 7 days, 30 minutes - 3 hours - 2 days, 5 hours
        duration_tracking: {
            [stageIds[0]]: 7 * 24 * 60 * 60 + 30 * 60,
            [stageIds[1]]: 3 * 60 * 60,
            [stageIds[3]]: 24 * 2 * 60 * 60 + 5 * 60 * 60,
        },
    });
    await start();
    await openFormView("res.partner", partnerId, {
        arch: `<form><field name="stage_id" widget="statusbar_duration"/></form>`,
    });
    await contains("span[title='7 days, 30 minutes']", {
        parent: [".o_statusbar_status button", { text: "New" }],
    });
    await contains("span[title='3 hours']", { parent: ["button", { text: "Qualified" }] });
    await contains("button", { text: "Proposition" });
    await contains("span[title='2 days, 5 hours']", { parent: ["button", { text: "Won" }] });
});
