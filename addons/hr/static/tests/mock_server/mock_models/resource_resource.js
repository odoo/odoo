import { ResourceResource } from "@resource/../tests/mock_server/mock_models/resource_resource";

import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { patch } from "@web/core/utils/patch";

patch(ResourceResource.prototype, {
    _get_store_avatar_card_fields() {
        return [
            ...super._get_store_avatar_card_fields(),
            "department_id",
            mailDataHelpers.Store.one(
                "employee_id",
                this.env["hr.employee"]._get_store_avatar_card_fields()
            ),
        ];
    },
});
