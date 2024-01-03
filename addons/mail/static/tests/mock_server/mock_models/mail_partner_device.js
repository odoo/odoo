/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class MailPartnerDevice extends models.ServerModel {
    _name = "mail.partner.device";

    /**
     * Simulates `get_web_push_vapid_public_key` on `mail.partner.device`.
     */
    get_web_push_vapid_public_key() {
        return btoa(crypto.randomUUID().replace(/-/g, ""));
    }
}
