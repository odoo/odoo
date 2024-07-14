/* @odoo-module */

import { Voip } from "@voip/core/voip_service";

import { patch } from "@web/core/utils/patch";

patch(Voip.prototype, {
    get areCredentialsSet() {
        return Boolean(this.settings.onsip_auth_username) && super.areCredentialsSet;
    },
    get authorizationUsername() {
        return this.settings.onsip_auth_username || "";
    },
});
