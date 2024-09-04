/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";
import { url } from "@web/core/utils/urls";
import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";

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
    storeAsTrackedImStatus = Record.one("Store", {
        /** @this {import("models").Persona} */
        compute() {
            if (
                this.type === "guest" ||
                (this.type === "partner" && this.im_status !== "im_partner" && !this.is_public)
            ) {
                return this._store;
            }
        },
        onAdd() {
            if (!this._store.env.services.bus_service.isActive) {
                return;
            }
            const model = this.type === "partner" ? "res.partner" : "mail.guest";
            this._store.env.services.bus_service.addChannel(`odoo-presence-${model}_${this.id}`);
        },
        onDelete() {
            if (!this._store.env.services.bus_service.isActive) {
                return;
            }
            const model = this.type === "partner" ? "res.partner" : "mail.guest";
            this._store.env.services.bus_service.deleteChannel(`odoo-presence-${model}_${this.id}`);
        },
        eager: true,
        inverse: "imStatusTrackedPersonas",
    });
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
        const urlParams = {};
        if (this.write_date) {
            urlParams.unique = this.write_date;
        }
        if (this.type === "partner") {
            return url("/web/image", {
                field: "avatar_128",
                id: this.id,
                model: "res.partner",
                ...urlParams,
            });
        }
        if (this.type === "guest") {
            return url("/web/image", {
                field: "avatar_128",
                id: this.id,
                model: "mail.guest",
                ...urlParams,
            });
        }
        if (this.user?.id) {
            return url("/web/image", {
                field: "avatar_128",
                id: this.user.id,
                model: "res.users",
                ...urlParams,
            });
        }
        return DEFAULT_AVATAR;
    }
}

Persona.register();
