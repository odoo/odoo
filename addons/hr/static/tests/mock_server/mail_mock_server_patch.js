import { patch } from "@web/core/utils/patch";
import { makeKwArgs } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

patch(mailDataHelpers, {
    _process_request_for_internal_user(store, name, params) {
        super._process_request_for_internal_user(...arguments);
        const ResUsers = this.env["res.users"];
        if (name === "avatar_card") {
            const userId = params.user_id;
            const [user] = ResUsers.browse(userId);
            if (user) {
                for (const [userField, fields] of Object.entries(
                    ResUsers._get_store_avatar_card_related_fields()
                )) {
                    let model;
                    if (userField === "department_id") {
                        model = this.env["hr.department"].browse(user.department_id);
                    } else if (userField === "work_location_id") {
                        model = this.env["hr.work.location"].browse(user.work_location_id);
                    } else if (userField === "employee_ids") {
                        model = this.env["hr.employee"].browse(user.employee_ids[0]);
                    }
                    if (model) {
                        store.add(
                            model,
                            makeKwArgs({
                                fields: fields,
                                id: model.id,
                            })
                        );
                    }
                }
            }
        }
    },
});
