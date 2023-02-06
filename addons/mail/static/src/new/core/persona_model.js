/* @odoo-module */

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {'partner'|'guest'} type
 * @property {ImStatus} im_status
 */

export class Persona {
    /** @type {string} */
    localId;
    /** @type {number} */
    id;
    /** @type {'partner' | 'guest'} */
    type;
    /** @type {string} */
    name;
    /** @type {{ code: string, id: number, name: string}|undefined} */
    country;
    /** @type {string} */
    email;
    /** @type {Array | undefined} */
    user;
    /** @type {ImStatus} */
    im_status;
    isAdmin = false;
    channelId;
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

    get avatarUrl() {
        switch (this.type) {
            case "partner":
                return `/mail/channel/1/partner/${this.id}/avatar_128`;
            case "guest":
                return `/mail/channel/${this.channelId}/guest/${this.id}/avatar_128?unique=${this.name}`;
            default:
                return "";
        }
    }
}
