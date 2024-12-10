import { Record } from "@mail/core/common/record";

export class ResPartner extends Record {
    static id = "id";
    static _name = "res.partner";
    /** @type {Object.<number, import("models").ResPartner>} */
    static records = {};
    /** @returns {import("models").ResPartner} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ResPartner|import("models").ResPartner[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    /** @type {number} */
    id;
    main_user = Record.one("res.users", {
        /** @this {import("models").ResPartner} */
        compute() {
            return this.user_ids.find((user) => user.share === false) || this.user_ids[0];
        },
    });
    persona = Record.one("Persona", {
        /** @this {import("models").ResPartner} */
        compute() {
            return { id: this.id, type: "partner" };
        },
        inverse: "partner",
    });
    user_ids = Record.many("res.users", { inverse: "partner_id" });
}

ResPartner.register();
