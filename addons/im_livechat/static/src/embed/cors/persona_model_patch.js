/* @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Persona.prototype, {
    get avatarUrl() {
        const params = assignDefined(
            {},
            {
                guest_token: this._store.env.services["im_livechat.livechat"].guestToken,
                unique: this.write_date,
            }
        );
        if (this.partnerId) {
            return url("/im_livechat/cors/web/image", {
                field: "avatar_128",
                id: this.id,
                model: "res.partner",
                ...params,
            });
        }
        if (this.guestId) {
            return url("/im_livechat/cors/web/image", {
                field: "avatar_128",
                id: this.id,
                model: "mail.guest",
                ...params,
            });
        }
        return super.avatarUrl;
    },
});
