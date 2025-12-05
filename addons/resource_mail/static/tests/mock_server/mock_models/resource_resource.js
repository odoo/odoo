import { ResourceResource } from "@resource/../tests/mock_server/mock_models/resource_resource";

import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { patch } from "@web/core/utils/patch";

patch(ResourceResource.prototype, {
    _get_store_avatar_card_fields() {
        return [
            "name",
            "resource_type",
            mailDataHelpers.Store.one(
                "user_id",
                this.env["res.users"]._get_store_avatar_card_fields()
            ),
        ];
    }
});
