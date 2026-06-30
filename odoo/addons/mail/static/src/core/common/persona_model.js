/* @odoo-module */

import { AND, Record } from "@mail/core/common/record";
import { debounce } from "@web/core/utils/timing";

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
    static new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => record.updateImStatus(newStatus),
            this.IM_STATUS_DEBOUNCE_DELAY
        );
        return record;
    }
    static IM_STATUS_DEBOUNCE_DELAY = 1000;

    channelMembers = Record.many("ChannelMember");
    /** @type {number} */
    id;
    /** @type {boolean | undefined} */
    is_company;
    /** @type {string} */
    landlineNumber;
    /** @type {string} */
    mobileNumber;
    debouncedSetImStatus;
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
    /** @type {{ code: string, id: number, name: string}|undefined} */
    country;
    /** @type {string} */
    email;
    /** @type {Array | Object | undefined} */
    user;
    /** @type {ImStatus} */
    im_status;
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

    updateImStatus(newStatus) {
        this.im_status = newStatus;
    }
}

Persona.register();
