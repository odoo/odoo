/* @odoo-module */

import { discussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { patch } from "@web/core/utils/patch";

patch(setupManager, "discuss/core/common", {
    setupServices(...args) {
        return {
            ...this._super(...args),
            "discuss.core.common": discussCoreCommon,
        };
    },
});
