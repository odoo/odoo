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
        { id: 1, name: "John Doe", job_id: 1 },
        { id: 2, name: "Jane Smith", job_id: false },
    ];
}

class ApplicantGetRefuseReason extends models.Model {
    _name = "applicant.get.refuse.reason";

    duplicate_applicant_ids = fields.Many2many({ relation: "hr.applicant" });

    _records = [{ id: 1, duplicate_applicant_ids: [1, 2] }];
}

defineMailModels();
defineModels([HrJob, HrApplicant, ApplicantGetRefuseReason]);

test("duplicate applicant tags show the job name", async () => {
    await mountView({
        type: "form",
        resModel: "applicant.get.refuse.reason",
        resId: 1,
        arch: `
            <form>
                <field name="duplicate_applicant_ids" widget="applicant_line_many2many"/>
            </form>`,
    });
    expect(queryAllTexts(".o_tag_badge_text")).toEqual(["Developer - John Doe", "Jane Smith"]);
});
