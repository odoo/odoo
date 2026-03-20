import { createElementWithContent } from "@web/core/utils/html";
import { fields, Record } from "@mail/model/export";
import { getOuterHtml } from "@mail/utils/common/html";

export class ResUsers extends Record {
    static _name = "res.users";
    static _inherits = { "res.partner": "partner_id" };

    /** @type {number} */
    id;
    company_id = fields.One("res.company");
    /** @type {string} */
    im_status;
    /** @type {boolean} */
    is_admin;
    /** @type {"email" | "inbox"} */
    notification_type;
    partner_id = fields.One("res.partner", { inverse: "user_ids" });
    /** @type {boolean} false when the user is an internal user, true otherwise */
    share;
    /** @type {ReturnType<import("@odoo/owl").markup>|string|undefined} */
    signature = fields.Html(undefined);

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
}

ResUsers.register();
