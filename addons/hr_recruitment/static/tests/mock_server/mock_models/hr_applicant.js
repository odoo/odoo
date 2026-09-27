import { models } from "@web/../tests/web_test_helpers";

export class HrApplicant extends models.ServerModel {
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
