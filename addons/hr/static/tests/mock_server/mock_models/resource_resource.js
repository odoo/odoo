import { ResourceResource } from "@resource/../tests/mock_server/mock_models/resource_resource";

import { patch } from "@web/core/utils/patch";

patch(ResourceResource.prototype, {
    _store_avatar_card_fields(res) {
        super._store_avatar_card_fields(res);
        res.one("department_id", ["name"]);
        res.one("employee_id", "_store_avatar_card_fields", { sudo: true });
    },
});
