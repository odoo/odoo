import { after, before, beforeAll, createJobScopedGetter } from "@odoo/hoot";

/**
 * @typedef {typeof SERVER_STATE_VALUES} ServerState
 */

const notifySubscribers = () => {
    // Apply new state to all subscribers
    for (const [target, callback] of subscriptions) {
        const descriptors = Object.getOwnPropertyDescriptors(callback(serverState));
        Object.defineProperties(target, descriptors);
    }
};

const SERVER_STATE_VALUES = {
    companyId: 1,
    companyName: "Hermit",
    debug: false,
    groupId: 11,
    lang: "en",
    multiLang: false,
    odoobotId: 418,
    partnerId: 17,
    partnerName: "Mitchell Admin",
    publicPartnerId: 18,
    publicPartnerName: "Public user",
    publicUserId: 8,
    timezone: "taht",
    userId: 7,
};

const getServerStateValues = createJobScopedGetter(
    (previousValues) => ({
        ...SERVER_STATE_VALUES,
        ...previousValues,
    }),
    notifySubscribers
);

/** @type {Map<any, (state: ServerState) => any>} */
const subscriptions = new Map([[odoo, (state) => ({ ...odoo, debug: state.debug })]]);

/**
 * @template T
 * @param {T} target
 * @param {(state: ServerState) => T} callback
 */
export function onServerStateChange(target, callback) {
    before(() => {
        subscriptions.set(target, callback);
    });
    after(() => {
        subscriptions.delete(target);
    });
}

export const serverState = new Proxy(SERVER_STATE_VALUES, {
    get(target, p) {
        return Reflect.get(getServerStateValues(), p);
    },
    set(target, p, newValue) {
        const result = Reflect.set(getServerStateValues(), p, newValue);
        if (result) {
            notifySubscribers();
        }
        return result;
    },
});

beforeAll(notifySubscribers);
