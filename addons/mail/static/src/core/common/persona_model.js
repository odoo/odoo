/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";
import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { imageUrl } from "@web/core/utils/urls";

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {'partner'|'guest'} type
 * @property {ImStatus} im_status
 */

export class Persona extends Record {
    static id = AND("type", "id");
    /** @type {Object.<number, import("models").Persona>} */
    static records = {};
    /** @returns {import("models").Persona} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Persona|import("models").Persona[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    channelMembers = Record.many("ChannelMember");
    /** @type {number} */
    id;
    /** @type {boolean | undefined} */
    is_company;
    /** @type {string} */
    landlineNumber;
    /** @type {string} */
    mobileNumber;
    /** @type {'partner' | 'guest'} */
    type;
    /** @type {string} */
    name;
    /** @type {string} */
    displayName;
    country = Record.one("Country");
    /** @type {string} */
    email;
    /** @type {Array | Object | undefined} */
    user;
    /** @type {ImStatus} */
    im_status;
    /** @type {'email' | 'inbox'} */
    notification_preference;
    isAdmin = false;
    /** @type {string} */
    write_date;

    /**
     * @returns {boolean}
     */
    get hasPhoneNumber() {
        return Boolean(this.mobileNumber || this.landlineNumber);
    }

    get nameOrDisplayName() {
        return this.name || this.displayName;
    }

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }

    get avatarUrl() {
        if (this.type === "partner") {
            return imageUrl("res.partner", this.id, "avatar_128", { unique: this.write_date });
        }
        if (this.type === "guest") {
            return imageUrl("mail.guest", this.id, "avatar_128", { unique: this.write_date });
        }
        if (this.user?.id) {
            return imageUrl("res.users", this.user.id, "avatar_128", { unique: this.write_date });
        }
        return DEFAULT_AVATAR;
    }
}

Persona.register();
