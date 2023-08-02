/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";
import { createObjectId } from "@mail/utils/common/misc";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaObjectId
 * @property {number} threadId
 */
export class ChannelMember extends DiscussModel {
    /** @type {number} */
    id;
    personaObjectId;
    rtcSessionId;
    threadId;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    get persona() {
        return this._store.Persona.records[this.personaObjectId];
    }

    set persona(persona) {
        this.personaObjectId = persona?.objectId;
    }

    get rtcSession() {
        return this._store.RtcSession.records[this.rtcSessionId];
    }

    get thread() {
        return this._store.Thread.records[
            createObjectId("Thread", "discuss.channel", this.threadId)
        ];
    }

    /**
     * @returns {string}
     */
    getLangName() {
        return this.persona.lang_name;
    }
}

export class ChannelMemberManager extends DiscussModelManager {
    /** @type {typeof ChannelMember} */
    class;
    /** @type {Object.<number, ChannelMember>} */
    records = {};
}

discussModelRegistry.add("ChannelMember", [ChannelMember, ChannelMemberManager]);
