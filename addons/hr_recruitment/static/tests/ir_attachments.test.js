import {
    click,
    defineMailModels,
    openView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, models } from "@web/../tests/web_test_helpers";

class HrApplicant extends models.ServerModel {
    _name = "hr.applicant";
    _records = [
        {
            id: 21,
        },
    ];
    _views = {
        form: `<form><field name="id"/></form>`,
    };
}
defineMailModels();
defineModels([HrApplicant]);

const newArchs = {
    "ir.attachment,false,list": `<list>
             <field name="res_id"/>
             <field name="res_model"/>
             <field name="res_name" widget="applicant_char"/>
         </list>`,
};

test("Recruitment applicant_char widget on ir.attachment", async () => {
    const pyEnv = await startServer();
    pyEnv["ir.attachment"]._fields.res_id.model_field = "res_model";
    pyEnv["ir.attachment"].create([
        { res_id: 21, res_model: "hr.applicant", res_name: "Someone" },
        { res_id: false, res_model: "hr.applicant", res_name: "Nobody" },
    ]);
    registerArchs(newArchs);
    await start();
    await openView({ res_model: "ir.attachment", views: [[false, "list"]] });
    await click(".o_field_applicant_char:last span");
    await animationFrame();
    expect(".o_field_applicant_char").toHaveCount(2);
    await click(".o_field_applicant_char:first span");
    await animationFrame();
    expect(".o_field_applicant_char").toHaveCount(0);
    expect('.o_field_widget[name="id"]:contains(21)').toHaveCount(1);
});
