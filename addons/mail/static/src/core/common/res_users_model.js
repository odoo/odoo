import { markup } from "@odoo/owl";
import { createElementWithContent } from "@web/core/utils/html";
import { fields, Record } from "@mail/core/common/record";

export class ResUsers extends Record {
    static _name = "res.users";
    static id = "id";

    /** @type {number} */
    id;
    company_id = fields.One("res.company");
    /** @type {string} */
    get email() {
        return this.partner_id?.email;
    }
    /** @type {string} */
    im_status;
    /** @type {boolean} */
    is_admin;
    /** @type {string} */
    get name() {
        return this.partner_id?.name;
    }
    /** @type {"email" | "inbox"} */
    notification_type;
    partner_id = fields.One("res.partner");
    /** @type {string} */
    get phone() {
        return this.partner_id?.phone;
    }
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
        return markup(divElement.outerHTML);
    }
}

ResUsers.register();
