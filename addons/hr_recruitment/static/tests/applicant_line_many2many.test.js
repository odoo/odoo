import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class HrJob extends models.Model {
    _name = "hr.job";

    name = fields.Char();

    _records = [{ id: 1, name: "Developer" }];
}

class HrApplicant extends models.Model {
    _name = "hr.applicant";

    name = fields.Char();
    job_id = fields.Many2one({ relation: "hr.job" });

    _records = [
        { id: 1, name: "Jane", job_id: 1 },
        { id: 2, name: "John", job_id: false },
    ];
}

class Wizard extends models.Model {
    applicant_ids = fields.Many2many({ relation: "hr.applicant" });

    _records = [{ id: 1, applicant_ids: [1, 2] }];
}

defineModels([HrJob, HrApplicant, Wizard]);
defineMailModels();

test("applicant tags are prefixed with the job name", async () => {
    await mountView({
        type: "form",
        resModel: "wizard",
        resId: 1,
        arch: `
            <form>
                <field name="applicant_ids" widget="applicant_line_many2many"/>
            </form>`,
    });
    expect(queryAllTexts(".o_tag")).toEqual(["Developer - Jane", "John"]);
});
