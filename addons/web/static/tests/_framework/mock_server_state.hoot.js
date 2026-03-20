// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { after, before, beforeEach, createJobScopedGetter } from "@odoo/hoot";
import { validateType } from "@odoo/owl";

const { view_info } = odoo.__session_info__ || {};
delete odoo.__session_info__;

const { Settings } = luxon;

/**
 * @typedef {typeof SERVER_STATE_VALUES} ServerState
 */

const applyDefaults = () => {
    Object.assign(Settings, DEFAULT_LUXON_SETTINGS);

    notifySubscribers();
};

const notifySubscribers = () => {
    // Apply new state to all subscribers
    for (const [target, callback] of subscriptions) {
        const descriptors = Object.getOwnPropertyDescriptors(callback(serverState));
        Object.defineProperties(target, descriptors);
    }
};

const DEFAULT_LUXON_SETTINGS = {
    defaultLocale: Settings.defaultLocale,
    defaultNumberingSystem: Settings.defaultNumberingSystem,
    defaultOutputCalendar: Settings.defaultOutputCalendar,
    defaultZone: Settings.defaultZone,
    defaultWeekSettings: Settings.defaultWeekSettings,
};
const SERVER_STATE_VALUES = {
    companies: [
        {
            id: 1,
            name: "Hermit",
            currency_id: 1,
        },
    ],
    currencies: [
        {
            id: 1,
            name: "USD",
            position: "before",
            symbol: "$",
        },
        {
            id: 2,
            name: "EUR",
            position: "after",
            symbol: "€",
        },
    ],
    db: "test",
    debug: "",
    groupId: 11,
    lang: "en",
    multiLang: false,
    odoobotId: 418,
    odoobotUid: 518,
    partnerId: 17,
    partnerName: "Mitchell Admin",
    publicPartnerId: 18,
    publicPartnerName: "Public user",
    publicUserId: 8,
    serverVersion: [1, 0, 0, "final", 0, ""],
    timezone: "taht",
    userContext: {},
    userId: 7,
    view_info,
};

const SERVER_STATE_VALUES_SCHEMA = {
    companies: { type: Array, element: Object },
    currencies: { type: Array, element: Object },
    db: String,
    debug: String,
    groupId: [Number, { value: false }],
    lang: String,
    multiLang: Boolean,
    odoobotId: [Number, { value: false }],
    partnerId: [Number, { value: false }],
    partnerName: String,
    publicPartnerId: [Number, { value: false }],
    publicPartnerName: String,
    publicUserId: Number,
    serverVersion: { type: Array, element: [String, Number] },
    timezone: String,
    userContext: Object,
    userId: [Number, { value: false }],
    view_info: Object,
};

const getServerStateValues = createJobScopedGetter(
    (previousValues) => ({
        ...JSON.parse(JSON.stringify(SERVER_STATE_VALUES)),
        ...previousValues,
    }),
    applyDefaults
);

/** @type {Map<any, (state: ServerState) => any>} */
const subscriptions = new Map([
    [
        odoo,
        ({ db, debug, serverVersion }) => ({
            ...odoo,
            debug,
            info: {
                db,
                server_version: serverVersion.slice(0, 2).join("."),
                server_version_info: serverVersion,
                isEnterprise: serverVersion.slice(-1)[0] === "e",
            },
            isReady: true,
        }),
    ],
]);

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
    deleteProperty(_target, p) {
        return Reflect.deleteProperty(getServerStateValues(), p);
    },
    get(_target, p) {
        return Reflect.get(getServerStateValues(), p);
    },
    has(_target, p) {
        return Reflect.has(getServerStateValues(), p);
    },
    set(_target, p, newValue) {
        if (p in SERVER_STATE_VALUES_SCHEMA && newValue !== null && newValue !== undefined) {
            const errorMessage = validateType(p, newValue, SERVER_STATE_VALUES_SCHEMA[p]);
            if (errorMessage) {
                throw new TypeError(errorMessage);
            }
        }
        const result = Reflect.set(getServerStateValues(), p, newValue);
        if (result) {
            notifySubscribers();
        }
        return result;
    },
});

beforeEach(applyDefaults, { global: true });
