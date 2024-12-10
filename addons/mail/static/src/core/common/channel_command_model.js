import { Record } from "@mail/core/common/record";

export class ChannelCommand extends Record {
    static id = "name";
    /** @type {Object.<number, import("models").ChannelCommand>} */
    static records = {};
    /** @returns {import("models").ChannelCommand} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ChannelCommand|import("models").ChannelCommand[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    endPosition;
    /** @type {string} */
    methodName;
    /** @type {string} */
    name;
    /** @type {Object} */
    subCommandData = {};
    /** @type {string[]} */
    subCommandFields = [];
    /** @type {boolean} */
    hasSubCommand;

    get params() {
        const res = {};
        for (const field of this.subCommandFields) {
            res[field] = this.subCommandData[field] ?? false;
        }
        return res;
    }
}

ChannelCommand.register();
