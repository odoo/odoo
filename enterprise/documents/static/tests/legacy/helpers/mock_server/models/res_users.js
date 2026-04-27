/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/res_users"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /** @override */
    _mockResUsers__init_store_data() {
        const res = super._mockResUsers__init_store_data(...arguments);
        res.Store.hasDocumentsUserGroup = true;
        return res;
    },
});
