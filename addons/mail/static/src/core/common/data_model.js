import { Record } from "@mail/core/common/record";

export class Data extends Record {
    static id = "id";
    /** @type {Object.<string, import("models").Data>} */
    static records = {};
    /** @returns {import("models").Data} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").Data[] : import("models").Data} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static createRequest() {
        return this.insert({ id: ++this._nextId });
    }
    static _nextId = 0;
    /** @type {number} */
    id;
    /*
     * Fields are contextual to each data request.
     * They are generically added here to benefit from fields behavior as well
     * as auto-complete, but their meaning depends on each data request.
     */
    attachments = Record.many("ir.attachment");
    channel = Record.one("Thread");
    channels = Record.many("Thread");
    /** @type {number} */
    count;
    message = Record.one("mail.message");
    partners = Record.many("Persona");
}

Data.register();
