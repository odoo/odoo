/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/res_partner"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(_route, { model, method, args }) {
        if (model !== "res.partner") {
            return super._performRPC(...arguments);
        }
        switch (method) {
            case "get_contacts":
                return this._mockResPartnerGetContacts(args);
            default:
                return super._performRPC(...arguments);
        }
    },
    /**
     * @returns {Object[]}
     */
    _mockResPartnerGetContacts() {
        return this._mockResPartner_FormatContacts(
            this.getRecords("res.partner", ["|", ["mobile", "!=", false], ["phone", "!=", false]])
        );
    },
    /**
     * @returns {Object[]}
     */
    _mockResPartner_FormatContacts(contacts) {
        return contacts.map((contact) => ({
            id: contact.id,
            displayName: contact.display_name,
            email: contact.email,
            landlineNumber: contact.phone,
            mobileNumber: contact.mobile,
            name: contact.display_name,
        }));
    },
});
