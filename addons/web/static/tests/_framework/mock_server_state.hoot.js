import { after, before, getCurrent } from "@odoo/hoot";

const applyDescriptors = (object, descriptors) => Object.defineProperties(object, descriptors);

const getDescriptors = (object) => Object.getOwnPropertyDescriptors(object);

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

const stateChangeInitiators = new WeakSet();
/** @type {Map<any, (state: typeof SERVER_STATE_VALUES) => any>} */
const subscriptions = new Map([[odoo, (state) => ({ ...odoo, debug: state.debug })]]);

/**
 * @template T
 * @param {T} target
 * @param {(state: typeof SERVER_STATE_VALUES) => T} callback
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
        return Reflect.get(target, p);
    },
    set(target, p, newValue) {
        const notifySubscribers = () => {
            for (const [target, callback] of subscriptions) {
                applyDescriptors(target, getDescriptors(callback(serverState)));
            }
        };

        const { suite, test } = getCurrent();
        const initiator = test || suite;
        if (!stateChangeInitiators.has(initiator)) {
            // Save initial state and restore it after the test
            stateChangeInitiators.add(initiator);
            const initialState = getDescriptors(target);

            after(() => {
                applyDescriptors(target, initialState);
                stateChangeInitiators.delete(initiator);

                notifySubscribers();
            });
        }

        const result = Reflect.set(target, p, newValue);
        if (result) {
            // Apply new state to all subscribers
            notifySubscribers();
        }
        return result;
    },
});
