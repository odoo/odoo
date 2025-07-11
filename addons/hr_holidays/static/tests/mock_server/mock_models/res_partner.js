import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    leave_date_to = fields.Date({ related: false });

    compute_im_status(partner) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        if (partner.main_user_id && ResUsers.browse(partner.main_user_id).leave_date_to) {
            if (partner.im_status === "online") {
                return "leave_online";
            } else if (partner.im_status === "away") {
                return "leave_away";
            } else {
                return "leave_offline";
            }
        } else {
            return super.compute_im_status(partner);
        }
    }

    /**
     * Overrides to add out of office to employees.
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["_to_store"]}
     */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        super._to_store(...arguments);
        for (const partner of this.browse(ids)) {
            if (partner.main_user_id) {
                store.add(
                    ResUsers.browse(partner.main_user_id),
                    makeKwArgs({ fields: ["employee_ids"] })
                );
            }
        }
    }
}
