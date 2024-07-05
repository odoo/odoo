// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { after, before, beforeEach, createJobScopedGetter } from "@odoo/hoot";

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

beforeEach(applyDefaults, { global: true });
