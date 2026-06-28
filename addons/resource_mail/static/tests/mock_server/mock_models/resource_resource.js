import { ResourceResource } from "@resource/../tests/mock_server/mock_models/resource_resource";

import { patch } from "@web/core/utils/patch";

patch(ResourceResource.prototype, {
    _store_avatar_card_fields(res) {
        res.one("user_id", "_store_avatar_card_fields");
        res.extend(["name", "resource_type"]);
    },
});
