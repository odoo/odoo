import { ImStatusMixin } from "@mail/core/common/im_status_mixin";

import { createElementWithContent } from "@web/core/utils/html";
import { fields } from "@mail/model/export";
import { getOuterHtml } from "@mail/utils/common/html";

import { imageUrl } from "@web/core/utils/urls";

export class ResUsers extends ImStatusMixin {
    static _name = "res.users";
    static _inherits = { "res.partner": "partner_id" };

    /** @type {number} */
    id;
    company_id = fields.One("res.company");
    /** @type {boolean} */
    is_admin;
    /** @type {boolean} */
    is_public;
    /** @type {"email" | "inbox"} */
    notification_type;
    partner_id = fields.One("res.partner", { inverse: "user_ids" });
    /** @type {boolean} false when the user is an internal user, true otherwise */
    share;
    /** @type {boolean} */
    active;
    /** @type {ReturnType<import("@odoo/owl").markup>|string|undefined} */
    signature = fields.Html(undefined);

    get avatarUrl() {
        if (this.partner_id) {
            return this.partner_id.avatarUrl;
        }
        return imageUrl("res.users", this.id, "avatar_128", { unique: this.write_date });
    }

    /**
     * Get the signature with its typical layout when inserted in html
     */
    getSignatureBlock() {
        if (!this.signature) {
            return "";
        }
        const divElement = document.createElement("div");
        divElement.setAttribute("data-o-mail-quote", "1");
        divElement.append(
            document.createElement("br"),
            document.createTextNode("-- "),
            document.createElement("br"),
            ...createElementWithContent("div", this.signature).childNodes
        );
        return getOuterHtml(divElement);
    }

    _computeMonitorPresence() {
        return super._computeMonitorPresence() && !this.is_public;
    }
}

ResUsers.register();
