// @ts-check

import {
    after,
    before,
    createJobScopedGetter,
    expect,
    getCurrent,
    mockFetch,
    mockLocation,
    mockWebSocket,
    registerDebugInfo,
} from "@odoo/hoot";
import { luxon } from "@web/core/l10n/luxon";
import { makeErrorFromResponse, rpc, RPCError } from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";
import { ensureArray, isIterable } from "@web/core/utils/collections/arrays";
import { isObject } from "@web/core/utils/collections/objects";
import { hashCode } from "@web/core/utils/format/strings";

import { serverState } from "../mock_server_state.hoot.js";
import {
    fetchModelDefinitions,
    globalCachedFetch,
    registerModelToFetch,
} from "../module_set.hoot.js";
import {
    DEFAULT_FIELD_PROPERTIES,
    getFieldDisplayName,
    S_SERVER_FIELD,
} from "./mock_fields.js";
import {
    getRecordQualifier,
    makeKwArgs,
    makeServerError,
    MockServerError,
    safeSplit,
} from "./mock_server_utils.js";

const { DateTime } = luxon;

/**
 * @typedef {{
 * type?: string;
 * [key: string]: any;
 * }} ActionDefinition
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 * @typedef {import("./mock_fields").FieldDefinition} FieldDefinition
 * @typedef {{
 * actionID?: string | number;
 * actionPath?: string;
 * parent_id?: MenuId;
 * appID?: MenuId;
 * children?: (MenuId | MenuDefinition)[];
 * id: MenuId;
 * name?: string;
 * webIcon?: string | false;
 * webIconData?: string;
 * xmlid?: string;
 * }} MenuDefinition
 * @typedef {number | "root"} MenuId
 * @typedef {MockServerBaseEnvironment & { [modelName: string]: Model }} MockServerEnvironment
 * @typedef {import("./mock_model").Model} Model
 * @typedef {import("./mock_model").ModelConstructor} ModelConstructor
 * @typedef {(this: MockServer, params: OrmParams) => unknown} OrmCallback
 * @typedef {{
 * args: any[];
 * kwargs: KwArgs;
 * method: string;
 * model: string;
 * parent: () => any;
 * request: Request;
 * route: string;
 * }} OrmParams
 * @typedef {[RegExp, Record<string, string>]} RouteMatcher
 * @typedef {{
 * final?: boolean;
 * pure?: boolean;
 * }} RouteOptions
 * @typedef {`${string}/${string}`} RoutePath
 * @typedef {{
 * actions?: Partial<MockServer["actions"]>;
 * lang?: string;
 * lang_parameters?: Partial<MockServer["_lang_parameters"]>;
 * menus?: MenuDefinition[];
 * models?: Iterable<ModelConstructor>;
 * modules?: Partial<MockServer["_modules"]>;
 * multi_lang?: import("../mock_server_state.hoot").ServerState["multiLang"];
 * routes?: any[];
 * timezone?: string;
 * translations?: Record<string, string>;
 * }} ServerParams
 * @typedef {import("@odoo/hoot").ServerWebSocket} ServerWebSocket
 * @typedef {string | Iterable<string> | RegExp} StringMatcher
 * @typedef {(string | RegExp)[]} StringMatchers
 */

/** @typedef {{ mode?: "add" | "replace"; }} DefineOptions */

/** @typedef {import("./mock_model").KwArgs} KwArgs */

/** @typedef {(this: MockServer, request: Request, params: Record<string, string>) => any} RouteCallback */

/** @param {import("./mock_model").ModelRecord} user */
function authenticateUser(user) {
    const { env } = MockServer;
    if (!user?.id) {
        throw new MockServerError("Unauthorized");
    }
    env.cookie.set("sid", user.id);
    env.uid = user.id;
}

/**
 * @param {any} object
 * @return {any}
 */
function deepCopy(object) {
    if (!object) {
        return object;
    }
    if (typeof object === "object") {
        if (object?.nodeType) {
            return object.cloneNode(true);
        } else if (object instanceof Date || object instanceof DateTime) {
            return new /** @type {any} */ (object).constructor(object);
        } else if (isIterable(object)) {
            const copy = [...object].map(deepCopy);
            if (object instanceof Set || object instanceof Map) {
                return new /** @type {any} */ (object).constructor(copy);
            } else {
                return copy;
            }
        } else {
            return Object.fromEntries(
                Object.entries(object).map(([key, object]) => [key, deepCopy(object)]),
            );
        }
    }
    return object;
}

/** @param {DefineOptions} [options] */
function getAssignAction(options) {
    const shouldAdd = options?.mode === "add";
    return function assign(target, key, value) {
        if (shouldAdd && target[key] === Object(target[key])) {
            if (Array.isArray(target[key])) {
                target[key].push(...value);
            } else {
                Object.assign(target[key], value);
            }
        } else {
            target[key] = value;
        }
    };
}

function getCurrentMockServer() {
    const { test } = getCurrent();
    if (!test || !test.run) {
        return null;
    }
    if (!mockServers.has(test.run)) {
        mockServers.set(test.run, new MockServer());
    }
    return mockServers.get(test.run);
}

/** @param {RequestInit} init */
function getJsonRpcParams({ headers, body }) {
    if (
        /** @type {any} */ (headers).get("Content-Type") !== "application/json" ||
        typeof body !== "string"
    ) {
        return null;
    }
    try {
        const parsedParams = JSON.parse(body);
        return {
            id: parsedParams.id,
            jsonrpc: parsedParams.jsonrpc,
        };
    } catch {
        return {
            id: nextJsonRpcId++,
            jsonrpc: "2.0",
        };
    }
}

/**
 * @param {MockServer["_models"]} models
 * @returns {any}
 */
function makeServerEnv(models) {
    const serverEnv = new MockServerBaseEnvironment();
    return new Proxy(serverEnv, {
        get: (target, p) => {
            if (p in target || typeof p !== "string" || p === "then") {
                return Reflect.get(target, p);
            }
            const model = Reflect.get(models, p);
            if (!model) {
                throw modelNotFoundError(
                    p,
                    "could not get model from server environment",
                );
            }
            return model;
        },
        has: (target, p) => Reflect.has(target, p) || Reflect.has(models, p),
    });
}

/**
 * @param {string} target
 * @param {StringMatchers} matchers
 */
function match(target, matchers) {
    return matchers.some(
        (matcher) =>
            matcher === "*" ||
            (matcher instanceof RegExp ? matcher.test(target) : target === matcher),
    );
}

/** @param {string} modelName */
function modelNotFoundError(modelName, consequence) {
    return new MockServerError(
        `Cannot find a definition for model "${modelName}": ${consequence} (did you forget to use \`defineModels()?\`)`,
    );
}

/** @param {Record<string, string> | Iterable<{ id: string, string: string }>} translations */
function parseTranslations(translations) {
    return isIterable(translations)
        ? translations
        : Object.entries(translations).map(([id, string]) => ({ id, string }));
}

/**
 * @param {any[]} a
 * @param {any[]} b
 * @returns {boolean}
 */
function isSameRouteDefinition(a, b) {
    return a.length === b.length && a.every((part, index) => part === b[index]);
}

/**
 * @param {Partial<ServerParams>} params
 * @param {DefineOptions} [options]
 */
function _defineParams(params, options) {
    const assign = getAssignAction(options);
    const currentParams = getCurrentParams();
    const appliedParams = { ...params };
    if (options?.mode === "add" && appliedParams.routes) {
        appliedParams.routes = appliedParams.routes.filter(
            (route) =>
                !currentParams.routes.some((existing) =>
                    isSameRouteDefinition(existing, route),
                ),
        );
        if (!appliedParams.routes.length) {
            delete appliedParams.routes;
        }
    }
    for (const [key, value] of Object.entries(appliedParams)) {
        assign(currentParams, key, value);
    }
    return MockServer.current?.configure(appliedParams);
}

const getCurrentParams = createJobScopedGetter(
    /** @param {ServerParams} previous */
    function getCurrentParams(previous) {
        const previousModels = previous?.models || _defaultMockModels;
        const previousRoutes = previous?.routes || _defaultMockRoutes;
        return {
            ...previous,
            actions: deepCopy(previous?.actions || []),
            menus: deepCopy(previous?.menus || [DEFAULT_MENU]),
            models: [...previousModels],
            routes: [...previousRoutes],
        };
    },
);

class MockServerBaseEnvironment {
    cookie = new Map();

    get companies() {
        return MockServer.env["res.company"].read(
            serverState.companies.map((c) => c.id),
        );
    }

    get company() {
        return this.companies[0];
    }

    /** @type {import("@web/core/context").Context} */
    get context() {
        return {
            lang: serverState.lang,
            tz: serverState.timezone,
            uid: serverState.userId,
        };
    }

    get lang() {
        return serverState.lang;
    }

    get uid() {
        return serverState.userId;
    }

    set uid(newUid) {
        serverState.userId = newUid;
        const user = this.user;
        if (user) {
            serverState.partnerId = user.partner_id;
        }
    }

    get user() {
        return MockServer.env["res.users"].browse(serverState.userId)[0];
    }
}

const ACTION_IDENTIFIERS = ["id", "xml_id", "path"];
const ACTION_TYPES = {
    actions: "ir.actions.actions",
    client: "ir.actions.client",
    close: "ir.actions.act_window_close",
    embedded: "ir.embedded.actions",
    report: "ir.actions.report",
    server: "ir.actions.server",
    todo: "ir.actions.todo",
    url: "ir.actions.act_url",
    view: "ir.actions.act_window.view",
    window: "ir.actions.act_window",
};
const ALLOWED_CHARS = {
    default: "[^/]",
    int: "\\d",
    path: ".",
    string: "[\\w:.-]",
};
const DEFAULT_MENU = {
    id: 1,
    appID: 1,
    name: "App1",
};
const ROOT_MENU = {
    id: "root",
    name: "root",
    appID: "root",
};

const INTERNAL_URL_PROTOCOLS = ["blob:", "data:"];

const EMOJI_STUB_CATEGORIES = [
    {
        name: "Smileys & Emotion",
        displayName: "Smileys & Emotion",
        title: "🙂",
        sortId: 1,
    },
    {
        name: "Animals & Nature",
        displayName: "Animals & Nature",
        title: "🐢",
        sortId: 3,
    },
    { name: "Food & Drink", displayName: "Food & Drink", title: "🍭", sortId: 4 },
];

const EMOJI_STUB_EMOJIS = [
    {
        category: "Smileys & Emotion",
        codepoints: "😀",
        emoticons: [],
        keywords: ["face", "grin", "grinning face"],
        name: "grinning face",
        shortcodes: [":grinning:"],
    },
    {
        category: "Smileys & Emotion",
        codepoints: "😃",
        emoticons: [":D", ":-D", "=D"],
        keywords: ["face", "mouth", "open", "smile", "grinning face with big eyes"],
        name: "grinning face with big eyes",
        shortcodes: [":smiley:"],
    },
    {
        category: "Smileys & Emotion",
        codepoints: "😉",
        emoticons: [";)", ";-)"],
        keywords: ["face", "wink", "winking face"],
        name: "winking face",
        shortcodes: [":wink:"],
    },
    {
        category: "Smileys & Emotion",
        codepoints: "❤️",
        emoticons: ["<3"],
        keywords: ["heart", "red heart"],
        name: "red heart",
        shortcodes: [":heart:"],
    },
    {
        category: "Animals & Nature",
        codepoints: "🐢",
        emoticons: [],
        keywords: ["animal", "reptile", "slow", "turtle"],
        name: "turtle",
        shortcodes: [":turtle:"],
    },
    {
        category: "Animals & Nature",
        codepoints: "🐍",
        emoticons: [],
        keywords: ["animal", "reptile", "snake"],
        name: "snake",
        shortcodes: [":snake:"],
    },
    {
        category: "Food & Drink",
        codepoints: "🍭",
        emoticons: [],
        keywords: ["candy", "dessert", "lollipop", "sweet"],
        name: "lollipop",
        shortcodes: [":lollipop:"],
    },
    {
        category: "Food & Drink",
        codepoints: "🍎",
        emoticons: [],
        keywords: ["apple", "fruit", "red apple"],
        name: "red apple",
        shortcodes: [":apple:"],
    },
];

const EMOJI_STUB_MODULE_SOURCE = `
const categories = ${JSON.stringify(EMOJI_STUB_CATEGORIES)};
const emojis = ${JSON.stringify(EMOJI_STUB_EMOJIS)};
let impl = null;
// A reset asked for before the real module is wired must not be dropped: the
// data it would have cleared is a module-level parse of TRANSLATED strings, so
// a test that patches translations and resets before starting (which is the
// only order that works -- the reset has to precede the parse) would otherwise
// keep whatever an earlier test parsed under different translations.
let resetPending = false;
export function getCategories() { return impl ? impl.getCategories() : categories; }
export function getEmojis() { return impl ? impl.getEmojis() : emojis; }
export function resetEmojiData() {
    if (impl) {
        impl.resetEmojiData?.();
    } else {
        resetPending = true;
    }
}
export async function __setImplUrl(url) {
    if (url === import.meta.url) {
        return;
    }
    impl = await import(url);
    if (resetPending) {
        resetPending = false;
        impl.resetEmojiData?.();
    }
}
`;

const EMOJI_STUB_MODULE_URL = `data:text/javascript;charset=utf-8,${encodeURIComponent(
    EMOJI_STUB_MODULE_SOURCE,
)}`;

/** @type {Record<string, () => object>} */
const HEAVY_STATIC_BUNDLE_STUBS = {
    "web.assets_emoji": () => ({
        is_esm: true,
        specifiers: ["@web/components/emoji_picker/emoji_data"],
        import_map: {
            "@web/components/emoji_picker/emoji_data": EMOJI_STUB_MODULE_URL,
        },
        files: {},
    }),
};

const R_DATASET_ROUTE = /\/web\/dataset\/call_(?:button|kw)\/[\w.-]+\/(?<step>\w+)/;
const R_ROUTE_PARAM = /<(?:(?<type>\w+):)?(?<name>[\w-]+)>/g;
const R_URL_SPECIAL_CHARACTERS = /[.$+()]/g;
const R_WEBCLIENT_ROUTE = /(?<step>\/web\/webclient\/\w+)/;
const R_WILDCARD = /\*+/g;

/** @type {WeakMap<() => any, MockServer>} */
const mockServers = new WeakMap();
/** @type {WeakSet<any>} */
const seenModels = new WeakSet();

/** @type {ModelConstructor[]} */
let _defaultMockModels = [];

/** @type {any[][]} */
let _defaultMockRoutes = [];

/** @param {Record<string, ModelConstructor> | ModelConstructor[]} ModelClasses */
export function setDefaultMockModels(ModelClasses) {
    const incoming = Object.values(ModelClasses);
    for (const ModelClass of incoming) {
        if (_defaultMockModels.includes(ModelClass)) {
            continue;
        }
        _defaultMockModels.push(ModelClass);
        if (/** @type {any} */ (ModelClass)._fetch) {
            registerModelToFetch(/** @type {any} */ (ModelClass).getModelName());
        }
    }
}

/** @param {any[]} args */
export function setDefaultMockRoute(...args) {
    _defaultMockRoutes.push(args);
}

let nextJsonRpcId = 1e9;

export class MockServer {
    /** @type {MockServer | null} */
    static get current() {
        const mockServer = getCurrentMockServer();
        return mockServer?._started ? mockServer : null;
    }

    static get env() {
        return this.current?.env;
    }

    static get state() {
        return serverState;
    }

    /** @type {ActionDefinition[]} */
    actions = [];
    /** @type {MenuDefinition[]} */
    menus = [];

    /** @private */
    _lang_parameters = {
        date_format: "%m/%d/%Y",
        decimal_point: ".",
        direction: "ltr",
        grouping: [3, 0],
        time_format: "%H:%M:%S",
        thousands_sep: ",",
        week_start: 7,
    };
    /**
     * @private
     * @type {Record<string, Model>}
     */
    _models = Object.create(null);
    /** @type {Set<string>} */
    _missingComputes = new Set();
    /**
     * @private
     * @type {Model[]}
     */
    _modelSpecs = [];
    /**
     * @private
     * @type {Set<string>}
     */
    _modelNamesToFetch = new Set();
    /** @private */
    _modules = {
        web: { messages: [] },
    };
    /**
     * @private
     * @type {[StringMatchers, StringMatchers, OrmCallback][]}
     */
    _ormListeners = [];
    /**
     * @private
     * @type {[[RegExp, boolean][], RouteCallback, RouteOptions][]}
     */
    _routes = [];
    /** @private */
    _started = false;
    /**
     * @private
     * @type {ServerWebSocket[]}
     */
    _websockets = [];

    env = makeServerEnv(this._models);

    /**
     * @param {Partial<ServerParams>} params
     * @param {DefineOptions} [options]
     */
    async configure(params, options) {
        const assign = getAssignAction(options);
        if (params.actions) {
            assign(this, "actions", params.actions);
        }
        if (params.lang) {
            assign(serverState, "lang", params.lang);
        }
        if (params.lang_parameters) {
            Object.assign(this._lang_parameters, params.lang_parameters);
        }
        if (params.menus) {
            assign(this, "menus", params.menus);
        }
        if (params.models) {
            assign(
                this,
                "_modelSpecs",
                [...params.models].map((ModelClass) =>
                    this._getModelDefinition(ModelClass),
                ),
            );
            if (this._started) {
                await this._loadModels();
            }
        }
        if (params.modules) {
            for (const [module, values] of Object.entries(params.modules)) {
                this._modules[module] ||= { messages: [] };
                assign(
                    this._modules[module],
                    "messages",
                    parseTranslations(/** @type {any} */ (values).message || values),
                );
            }
        }
        if (params.multi_lang) {
            assign(serverState, "multiLang", params.multi_lang);
        }
        if (params.timezone) {
            assign(serverState, "timezone", params.timezone);
        }
        if (params.translations) {
            assign(
                this._modules.web,
                "messages",
                parseTranslations(params.translations),
            );
        }
        if (params.routes) {
            for (const args of params.routes) {
                const rpcArgs = Array.isArray(args) ? args : [args];
                /** @type {Function} */ (this._onRpc).apply(this, rpcArgs);
            }
        }

        return this;
    }

    /** @param {string} [url] */
    getWebSockets(url) {
        return url
            ? this._websockets.filter((ws) => ws.url.includes(url))
            : this._websockets;
    }

    async start() {
        if (this._started) {
            throw new MockServerError("MockServer has already been _started");
        }
        this._started = true;

        registerDebugInfo("mock server", this);

        const rpcCache = new RPCCache("mockRpc", 1, "23aeb0ff5d46cfa8aa44163720d871ac");
        rpc.setCache(rpcCache);
        after(async () => {
            rpc.setCache(null);
            await rpcCache.indexedDB?.deleteDatabase();
        });

        mockFetch(/** @type {any} */ (this._handleRequest.bind(this)));
        mockWebSocket(this._handleWebSocket.bind(this));

        this._onRoute(["/web/action/load"], this.loadAction);
        this._onRoute(["/web/action/load_breadcrumbs"], this.loadActionBreadcrumbs);
        this._onRoute(["/web/bundle/<string:bundle_name>"], this.loadBundle);
        this._onRoute(
            [
                "/web/dataset/call_kw",
                "/web/dataset/call_kw/<path:path>",
                "/web/dataset/call_button",
                "/web/dataset/call_button/<path:path>",
            ],
            this.callKw,
            { final: true },
        );
        this._onRoute(["/web/dataset/resequence"], this.resequence);
        this._onRoute(
            ["/web/image/<string:model>/<int:id>/<string:field>"],
            /** @type {any} */ (this.loadImage),
        );
        this._onRoute(["/web/webclient/load_menus"], this.loadMenus);
        this._onRoute(["/web/webclient/translations"], this.loadTranslations);

        await this.configure(/** @type {any} */ (getCurrentParams()));

        return this;
    }

    /**
     * @private
     * @param {OrmParams} params
     */
    _callOrm(params) {
        const { args, method, model: modelName, kwargs } = params;

        if (modelName) {
            const model = this.env[modelName];
            if (typeof model[method] === "function") {
                const expectedLength = model[method].length;
                while (args.length < expectedLength) {
                    args.push(undefined);
                }
                return model[method](...args, kwargs);
            }

            for (const parentName of safeSplit(model._inherit)) {
                const parentModel = this.env[parentName];
                if (typeof parentModel[method] === "function") {
                    const expectedLength = parentModel[method].length;
                    while (args.length < expectedLength) {
                        args.push(undefined);
                    }
                    return parentModel[method].call(model, ...args, kwargs);
                }
            }
        }

        throw new MockServerError(`Unimplemented ORM method: ${modelName}.${method}`);
    }

    /**
     * @private
     * @param {string | number | false} id
     */
    _findAction(id) {
        const strId = String(id);
        const actions = this.actions.filter((action) => {
            for (const identifier of ACTION_IDENTIFIERS) {
                if (String(action[identifier]) === strId) {
                    return action;
                }
            }
        });
        if (!actions.length) {
            throw makeServerError({
                errorName: "odoo.addons.web.controllers.action.MissingActionError",
                message: `The action ${JSON.stringify(id)} does not exist`,
            });
        }
        return this._getAction(Object.assign({}, ...actions));
    }

    /**
     * @private
     * @param {OrmParams} params
     */
    _findOrmListeners({ method, model }) {
        const callbacks = [this._callOrm];
        for (const [modelMatchers, methodMatchers, callback] of this._ormListeners) {
            if (match(model, modelMatchers) && match(method, methodMatchers)) {
                callbacks.unshift(callback);
            }
        }
        return callbacks;
    }

    /**
     * @private
     * @param {URL} url
     */
    _findRouteListeners(url) {
        const fullRoute = INTERNAL_URL_PROTOCOLS.includes(url.protocol)
            ? url.href
            : url.origin + url.pathname;
        /** @type {[RouteCallback, Record<string, string>, RouteOptions][]} */
        const listeners = [];
        for (const [routeRegexes, callback, options] of this._routes) {
            for (const [regex, partialMatch] of routeRegexes) {
                const routePart = partialMatch ? url.pathname : fullRoute;
                const argsMatch = routePart.match(regex);
                if (argsMatch) {
                    listeners.unshift([callback, argsMatch.groups, options]);
                }
            }
        }
        const seen = new Set();
        return listeners.filter(([callback]) => {
            if (seen.has(callback)) {
                return false;
            }
            seen.add(callback);
            return true;
        });
    }

    /**
     * @private
     * @param {Partial<ActionDefinition>} rawAction
     */
    _getAction(rawAction) {
        const mainIdentifier = ACTION_IDENTIFIERS.find(
            (identifier) => rawAction[identifier],
        );
        const id = rawAction[mainIdentifier];
        /** @type {any} */
        const action = {
            binding_type: "action",
            binding_view_types: "list,form",
            id,
            type: ACTION_TYPES.window,
            xml_id: id,
            ...rawAction,
        };
        switch (action.type) {
            case ACTION_TYPES.client: {
                action.context ||= {};
                action.target ??= "current";
                break;
            }
            case ACTION_TYPES.embedded: {
                action.context ||= {};
                action.domain ||= [];
                action.filter_ids ||= [];
                action.groups_id ||= [];
                break;
            }
            case ACTION_TYPES.report: {
                action.binding_type = rawAction.binding_type ?? "report";
                action.report_type ??= "qweb-pdf";
                action.groups_id ||= [];
                break;
            }
            case ACTION_TYPES.server: {
                action.available_model_ids ||= [];
                action.child_ids ||= [];
                action.code ??= "";
                action.evaluation_type ??= "value";
                action.groups_id ||= [];
                action.sequence ??= 5;
                action.state ??= "object_write";
                action.update_boolean_value ??= "true";
                action.update_m2m_operation ??= "add";
                action.usage ??= "ir_actions_server";
                action.webhook_field_ids ||= [];
                break;
            }
            case ACTION_TYPES.todo: {
                action.sequence ??= 10;
                action.state ??= "open";
                break;
            }
            case ACTION_TYPES.url: {
                action.target ??= "new";
                break;
            }
            case ACTION_TYPES.window: {
                action.context ||= {};
                action.embedded_action_ids ||= [];
                action.group_ids ||= [];
                action.limit ??= 80;
                action.mobile_view_mode ??= "kanban";
                action.target ??= "current";
                action.view_ids ||= [];
                action.view_mode ??= "list,form";
                action.cache ??= true;
                for (const embeddedAction of this.actions) {
                    if (
                        embeddedAction.type === ACTION_TYPES.embedded &&
                        embeddedAction.parent_action_id === id
                    ) {
                        action.embedded_action_ids.push(
                            this._getAction(embeddedAction),
                        );
                    }
                }
                break;
            }
            default: {
                if (!(action.type in ACTION_TYPES)) {
                    throw new MockServerError(
                        `Invalid action type "${action.type}" in action ${id}`,
                    );
                }
            }
        }
        return action;
    }

    /**
     * @private
     * @param {ModelConstructor} ModelClass
     * @returns {Model}
     */
    _getModelDefinition(ModelClass) {
        const model = ModelClass.definition;

        if (/** @type {any} */ (ModelClass)._fetch) {
            this._modelNamesToFetch.add(model._name);
        }

        return model;
    }

    /**
     * @private
     * @param {string | URL} input
     * @param {RequestInit} init
     */
    async _handleRequest(input, init) {
        const request = new Request(input, init);
        const url = new URL(request.url);
        let jsonRpcParams = getJsonRpcParams(init);
        let error = null;
        let result = null;

        const listeners = this._findRouteListeners(url);
        if (!listeners.length && !INTERNAL_URL_PROTOCOLS.includes(url.protocol)) {
            if (url.origin === mockLocation.origin) {
                error = new MockServerError(
                    `Unimplemented server route: ${url.pathname}`,
                );
            } else {
                error = new MockServerError(
                    `Unimplemented server external URL: ${url.origin + url.pathname}`,
                );
            }
        } else {
            for (const [callback, routeParams, { final, pure }] of listeners) {
                try {
                    const callbackResult = await callback.call(
                        this,
                        request,
                        routeParams,
                    );
                    if (result instanceof Error) {
                        error = callbackResult;
                    } else {
                        result = callbackResult;
                    }
                } catch (err) {
                    error = err instanceof Error ? err : new Error(err);
                }
                if (final || error || (result !== null && result !== undefined)) {
                    if (pure || result instanceof Response) {
                        jsonRpcParams = null;
                    }
                    break;
                }
            }
        }

        if (jsonRpcParams) {
            if (error) {
                if (error instanceof RPCError) {
                    jsonRpcParams.error = {
                        code: Number.isInteger(error.code) ? error.code : 200,
                        message: error.message || "Odoo Server Error",
                        data: error.data,
                        type: error.subType ?? undefined,
                    };
                } else {
                    jsonRpcParams.error = {
                        ...makeErrorFromResponse({
                            code: 200,
                            data: {
                                name: error.name,
                                message: error.message,
                                subType: error.type,
                            },
                            message: error.message,
                            type: error.name,
                        }),
                    };
                }
                return jsonRpcParams;
            } else {
                jsonRpcParams.result = result === undefined ? null : result;
                return jsonRpcParams;
            }
        } else if (error) {
            throw error;
        } else {
            return result;
        }
    }

    /**
     * @private
     * @param {ServerWebSocket} webSocket
     */
    _handleWebSocket(webSocket) {
        this._websockets.push(webSocket);
    }

    /** @private */
    async _loadModels() {
        const models = this._modelSpecs;
        const serverModelInheritances = new Set();
        this._modelSpecs = [];

        let serverModels = {};
        if (this._modelNamesToFetch.size) {
            serverModels = await fetchModelDefinitions(this._modelNamesToFetch);
            this._modelNamesToFetch.clear();
        }

        for (const model of models) {
            if (model._name in serverModels) {
                const {
                    description,
                    fields,
                    inherit,
                    order,
                    parent_name,
                    rec_name,
                    ...otherProperties
                } = serverModels[model._name];

                if (description) {
                    model._description = description;
                }
                if (order) {
                    model._order = order;
                }
                if (parent_name) {
                    model._parent_name = parent_name;
                }
                if (rec_name) {
                    model._rec_name = rec_name;
                }

                if (inherit?.length) {
                    const inheritList = new Set(safeSplit(model._inherit));
                    for (const inherittedModelName of inherit) {
                        inheritList.add(inherittedModelName);
                        serverModelInheritances.add(
                            [model._name, inherittedModelName].join(","),
                        );
                    }
                    model._inherit = [...inheritList].join(",");
                }

                for (const [fieldName, serverField] of Object.entries(fields)) {
                    model._fields[fieldName] = {
                        ...DEFAULT_FIELD_PROPERTIES,
                        ...serverField,
                        ...model._fields[fieldName],
                        [S_SERVER_FIELD]: true,
                    };
                }

                Object.assign(model, otherProperties);
            }

            if (model._rec_name) {
                if (!(model._rec_name in model._fields)) {
                    throw new MockServerError(
                        `Invalid _rec_name "${String(model._rec_name)}" on model "${model._name}": field does not exist`,
                    );
                }
            } else if ("name" in model._fields) {
                /** @type {any} */ (model)._rec_name = "name";
            } else if ("x_name" in model._fields) {
                /** @type {any} */ (model)._rec_name = "x_name";
            }

            if (model._name in this._models) {
                const existingModel = this._models[model._name];
                for (const fieldName in existingModel._fields) {
                    model._fields[fieldName] ??= existingModel._fields[fieldName];
                }
                const modelProto = Object.getPrototypeOf(model);
                let wouldCycle =
                    modelProto === existingModel || existingModel === model;
                let walker = existingModel;
                while (!wouldCycle && walker) {
                    if (walker === modelProto) {
                        wouldCycle = true;
                        break;
                    }
                    walker = Object.getPrototypeOf(walker);
                }
                if (!wouldCycle) {
                    Object.setPrototypeOf(modelProto, existingModel);
                }
            } else if (model._name in this.env) {
                throw new MockServerError(
                    `Cannot register model "${model._name}": a server environment property with the same name already exists`,
                );
            }

            this._models[model._name] = model;
        }

        for (const model of models) {
            for (const modelName of safeSplit(model._inherit)) {
                if (!modelName) {
                    continue;
                }
                const parentModel = this._models[modelName];
                if (parentModel) {
                    for (const fieldName in parentModel._fields) {
                        model._fields[fieldName] ??= parentModel._fields[fieldName];
                    }
                } else if (
                    serverModelInheritances.has([model._name, modelName].join(","))
                ) {
                    model._inherit = safeSplit(model._inherit)
                        .filter((name) => name !== modelName)
                        .join(",");
                } else {
                    throw modelNotFoundError(modelName, "could not inherit from model");
                }
            }

            for (const [fieldName, field] of Object.entries(model._fields)) {
                if (field.relation && !this._models[field.relation]) {
                    if (field[S_SERVER_FIELD]) {
                        delete model._fields[fieldName];
                        continue;
                    } else {
                        throw modelNotFoundError(
                            field.relation,
                            "could not find model",
                        );
                    }
                }

                field.name = fieldName;
                field.string ||= getFieldDisplayName(fieldName);

                const onChange = field.onChange;
                if (typeof onChange === "function") {
                    model._onChanges[fieldName] ||= onChange.bind(model);
                }

                if (field.compute) {
                    /** @type {any} */
                    let computeFn = field.compute;
                    if (typeof computeFn !== "function") {
                        const computeName = computeFn;
                        computeFn = /** @type {any} */ (model)[computeName];
                        if (typeof computeFn !== "function") {
                            const key = `${model._name}.${fieldName}:${computeName}`;
                            if (!this._missingComputes.has(key)) {
                                this._missingComputes.add(key);
                                console.debug(
                                    `[asset.mockserver] dropping compute "${computeName}" on ` +
                                        `${model._name}.${fieldName}: method not reachable from ` +
                                        `${model.constructor?.name} prototype chain (likely ` +
                                        `cross-test field merge)`,
                                );
                            }
                            continue;
                        }
                    }

                    model._computes[fieldName] = computeFn;
                } else if (field.related) {
                    model._related.add(fieldName);
                }
            }

            const recordsWithoutId = [];
            const seenIds = new Set();
            for (const record of model._records) {
                for (const fieldName in record) {
                    if (!(fieldName in model._fields)) {
                        throw new MockServerError(
                            `Unknown field "${fieldName}" on ${getRecordQualifier(
                                /** @type {any} */ (record),
                            )} in model "${model._name}"`,
                        );
                    }
                }
                if (record.id) {
                    if (seenIds.has(record.id)) {
                        throw new MockServerError(
                            `Duplicate ID ${record.id} in model "${model._name}"`,
                        );
                    }
                    seenIds.add(record.id);
                } else {
                    recordsWithoutId.push(record);
                }
                /** @type {any} */ (model).push(record);
            }
            model._records = [];

            for (const record of recordsWithoutId) {
                record.id = /** @type {any} */ (model)._getNextId();
            }
        }

        for (const model of models) {
            for (const record of model) {
                /** @type {any} */ (model)._applyDefaults(record);
            }
            /** @type {any} */ (model)._applyComputesAndValidate();
        }

        const IrModelFields = this._models["ir.model.fields"];
        if (IrModelFields) {
            for (const model of models) {
                for (const field of Object.values(model._fields)) {
                    if (field.tracking) {
                        IrModelFields.create(
                            /** @type {any} */ ({
                                model: model._name,
                                name: field.name,
                                ttype: field.type,
                            }),
                        );
                    }
                }
            }
        }
    }

    /**
     * @overload
     * @param {OrmCallback} callback
     */

    /**
     * @overload
     * @param {StringMatchers} method
     * @param {OrmCallback} callback
     */

    /**
     * @overload
     * @param {StringMatchers} model
     * @param {StringMatcher} method
     * @param {OrmCallback} callback
     */
    /** @private */
    _onOrmMethod(...args) {
        /** @type {OrmCallback[]} */
        const [callback] = ensureArray(args.pop());
        /** @type {StringMatchers} */
        const method = ensureArray(args.pop() || "*");
        /** @type {StringMatchers} */
        const model = ensureArray(args.pop() || "*");

        if (typeof callback !== "function") {
            throw new MockServerError(
                `onRpc: expected callback to be a function, got: ${callback}`,
            );
        }

        this._ormListeners.push([model, method, callback]);
    }

    /**
     * @private
     * @param {RoutePath[]} routes
     * @param {RouteCallback} callback
     * @param {RouteOptions} [options]
     */
    _onRoute(routes, callback, options) {
        const routeRegexes = routes.map((route) => {
            const regexString = route
                .replaceAll(R_URL_SPECIAL_CHARACTERS, "\\$&")
                .replaceAll(R_ROUTE_PARAM, (...args) => {
                    const { name, type } = args.pop();
                    return `(?<${name}>${ALLOWED_CHARS[type] || ALLOWED_CHARS.default}+)`;
                })
                .replaceAll(R_WILDCARD, ".*");
            return [new RegExp(`^${regexString}$`, "i"), route.startsWith("/")];
        });

        this._routes.push([/** @type {any} */ (routeRegexes), callback, options || {}]);
    }

    /**
     * @overload
     * @param {OrmCallback} callback
     */

    /**
     * @overload
     * @param {RoutePath | Iterable<RoutePath>} route
     * @param {RouteCallback} callback
     * @param {RouteOptions} [options]
     */

    /**
     * @overload
     * @param {StringMatcher} method
     * @param {OrmCallback} callback
     */

    /**
     * @overload
     * @param {StringMatcher} model
     * @param {StringMatcher} method
     * @param {OrmCallback} callback
     */
    /** @private */
    _onRpc(...args) {
        const ormArgs = [];
        const routeArgs = [];
        for (const val of ensureArray(args.shift())) {
            if (typeof val === "string" && val.includes("/")) {
                routeArgs.push(val);
            } else {
                ormArgs.push(val);
            }
        }
        if (ormArgs.length) {
            /** @type {Function} */ (this._onOrmMethod).call(this, ormArgs, ...args);
        }
        if (routeArgs.length) {
            /** @type {Function} */ (this._onRoute).call(this, routeArgs, ...args);
        }
        return this;
    }

    async callKw(request) {
        const callNextOrmCallback = () => {
            const nextCallback = ormListeners.shift();
            return nextCallback.call(this, callbackParams);
        };

        const { params } = await request.json();
        params.args ||= [];
        params.kwargs = makeKwArgs(params.kwargs || {});
        const callbackParams = {
            parent: callNextOrmCallback,
            request,
            route: new URL(request.url).pathname,
            ...params,
        };
        const ormListeners = this._findOrmListeners(params);
        while (ormListeners.length) {
            const result = await callNextOrmCallback();
            if (result !== null && result !== undefined) {
                return result;
            }
        }
        return null;
    }

    async loadAction(request) {
        const { params } = await request.json();
        return this._findAction(params.action_id);
    }

    async loadActionBreadcrumbs(request) {
        const { params } = await request.json();
        const { actions } = params;
        return actions.map(({ action: actionId, model, resId }) => {
            /** @type {string} */
            let displayName;
            if (actionId) {
                const action = this._findAction(actionId);
                if (resId) {
                    displayName =
                        this.env[action.res_model].browse(resId)[0].display_name;
                } else {
                    displayName = action.name;
                }
            } else if (model) {
                if (!resId) {
                    throw new MockServerError(
                        "Actions with a 'model' should also have a 'resId'",
                    );
                }
                displayName = this.env[model].browse(resId)[0].display_name;
            } else {
                throw new MockServerError(
                    "Actions should have either an 'action' (ID or path) or a 'model'",
                );
            }
            return { display_name: displayName };
        });
    }

    /**
     * @param {Request} request
     * @param {Record<string, string>} params
     */
    async loadBundle(request, { bundle_name }) {
        const stubFactory = HEAVY_STATIC_BUNDLE_STUBS[bundle_name];
        if (stubFactory) {
            return new Response(JSON.stringify(stubFactory()), {
                headers: { "Content-Type": "application/json" },
            });
        }
        const initiatorTestId = getCurrent().test?.id;
        if (initiatorTestId) {
            const result = await globalCachedFetch(request.url);
            if (initiatorTestId === getCurrent().test?.id) {
                return result;
            }
        }
        throw new MockServerError(
            `loadBundle("${bundle_name}") was superseded: the initiating test ended before the bundle finished loading`,
        );
    }

    async loadImage(request, { id, model, field }) {
        return `<fake url to record ${id} on ${model}.${field}>`;
    }

    async loadMenus() {
        /** @type {any} */
        const allChildIds = new Set();
        /** @type {any} */
        const menuDict = {};
        /** @type {any[]} */
        const menuStack = [{ ...ROOT_MENU, children: this.menus }];
        while (menuStack.length) {
            const menu = menuStack.shift();
            /** @type {any} */
            const childIds = new Set();
            menuDict[menu.id] = { ...menuDict[menu.id], ...menu };
            for (const childMenuOrId of menuDict[menu.id].children) {
                let childId = childMenuOrId;
                if (isObject(childMenuOrId)) {
                    childId = childMenuOrId.id;
                    menuStack.push({
                        appID: childId,
                        children: [],
                        name: `App${childId}`,
                        ...childMenuOrId,
                    });
                }
                allChildIds.add(childId);
                childIds.add(childId);
            }
            menuDict[menu.id].children = [...childIds].sort((a, b) => a - b);
        }
        const missingMenuIds = [...allChildIds].filter((id) => !(id in menuDict));
        if (missingMenuIds.length) {
            throw new MockServerError(
                `Missing menu ID(s): ${missingMenuIds.join(", ")}`,
            );
        }
        return menuDict;
    }

    async loadTranslations(request) {
        const requestHash = new URL(request.url).searchParams.get("hash");
        /** @type {any} */
        const langParameters = { ...this._lang_parameters };
        if (typeof langParameters.grouping !== "string") {
            langParameters.grouping = JSON.stringify(langParameters.grouping);
        }
        const result = {
            lang: serverState.lang,
            lang_parameters: langParameters,
            modules: this._modules,
            multi_lang: serverState.multiLang,
        };

        const currentHash = /** @type {any} */ (hashCode)(
            JSON.stringify(result),
        ).toString(16);
        if (currentHash === requestHash) {
            return {
                lang: serverState.lang,
                hash: currentHash,
                no_change: true,
            };
        }
        /** @type {any} */ (result).hash = currentHash;
        return result;
    }

    async resequence(request) {
        const { params } = await request.json();
        const offset = params.offset ? Number(params.offset) : 0;
        const field = params.field || "sequence";
        if (!(field in this.env[params.model]._fields)) {
            return false;
        }
        for (const index in params.ids) {
            const record = this.env[params.model].find(
                (r) => r.id === params.ids[index],
            );
            record[field] = Number(index) + offset;
        }
        return true;
    }
}

/**
 * @param {string} login
 * @param {string} password
 */
export function authenticate(login, password) {
    const { env } = MockServer;
    const [user] = /** @type {any} */ (env["res.users"])._filter(
        [
            ["login", "=", login],
            ["password", "=", password],
        ],
        { active_test: false },
    );
    authenticateUser(user);
    env.cookie.set("authenticated_user_sid", env.cookie.get("sid"));
}

/**
 * @param {ActionDefinition[]} actions
 * @param {DefineOptions} [options]
 */
export function defineActions(actions, options) {
    before(() => _defineParams({ actions }, { mode: "add", ...options }));
}

/**
 * @param {MenuDefinition[]} menus
 * @param {DefineOptions} [options]
 */
export function defineMenus(menus, options) {
    before(() => _defineParams({ menus }, { mode: "add", ...options }));
}

/**
 * @param {ModelConstructor[] | Record<string, ModelConstructor>} ModelClasses
 * @param {DefineOptions} [options]
 */
export function defineModels(ModelClasses, options) {
    const models = Object.values(ModelClasses);
    // A mock model may carry the routes its addon's client reaches it through
    // (`static _mockRoutes = [[route, handler], ...]`), so that a helper which
    // spreads another addon's models gets that addon's routes with them. mail's
    // routes used to be registered only by defineMailModels(), and every helper
    // that spread mailModels into a bare defineModels() -- sms, calendar,
    // snailmail and forty more -- served a chatter no /mail route answered.
    const routes = [];
    for (const ModelClass of models) {
        const RouteModelClass = /** @type {any} */ (ModelClass);
        routes.push(...(RouteModelClass._mockRoutes ?? []));
        if (seenModels.has(ModelClass)) {
            continue;
        }
        seenModels.add(ModelClass);
        if (/** @type {any} */ (ModelClass)._fetch) {
            registerModelToFetch(/** @type {any} */ (ModelClass).getModelName());
        }
    }
    before(() =>
        _defineParams(
            /** @type {any} */ (routes.length ? { models, routes } : { models }),
            { mode: "add", ...options },
        ),
    );
}

/**
 * @param {ServerParams} params
 * @param {DefineOptions} [options]
 */
export function defineParams(params, options) {
    before(() => _defineParams(params, options));
}

export function logout() {
    const { env } = MockServer;
    if (env.cookie.get("authenticated_user_sid") === env.cookie.get("sid")) {
        env.cookie.delete("authenticated_user_sid");
    }
    env.cookie.delete("sid");
    const [publicUser] = /** @type {any} */ (env["res.users"]).browse(
        serverState.publicUserId,
        {
            active_test: false,
        },
    );
    authenticate(publicUser.login, publicUser.password);
}

/** @returns {Promise<MockServer>} */
export async function makeMockServer() {
    return getCurrentMockServer().start();
}

/**
 * @overload
 * @param {OrmCallback} callback
 * @returns {void}
 */

/**
 * @overload
 * @param {RoutePath | Iterable<RoutePath>} route
 * @param {RouteCallback} callback
 * @param {RouteOptions} [options]
 * @returns {void}
 */

/**
 * @overload
 * @param {StringMatcher} method
 * @param {OrmCallback} callback
 * @returns {void}
 */

/**
 * @overload
 * @param {StringMatcher} model
 * @param {StringMatcher} method
 * @param {OrmCallback} callback
 * @returns {void}
 */
/**
 * @param {...any} args
 * @returns {void}
 */
export function onRpc(...args) {
    before(() =>
        _defineParams(/** @type {any} */ ({ routes: [args] }), { mode: "add" }),
    );
}

const STEP_TRACKER_BOILERPLATE_METHODS = new Set(["lazy_session_info", "get_badges"]);
const STEP_TRACKER_BOILERPLATE_ROUTES = new Set(["/mail/data", "/mail/action"]);

/** @returns {void} */
export function stepAllNetworkCalls() {
    onRpc("/*", (request) => {
        const route = new URL(request.url).pathname;
        let match = route.match(R_DATASET_ROUTE);
        if (match) {
            const step = match.groups?.step || route;
            if (STEP_TRACKER_BOILERPLATE_METHODS.has(step)) {
                return;
            }
            return void expect.step(step);
        }
        match = route.match(R_WEBCLIENT_ROUTE);
        if (match) {
            return void expect.step(match.groups?.step || route);
        }
        if (STEP_TRACKER_BOILERPLATE_ROUTES.has(route)) {
            return;
        }
        return void expect.step(route);
    });
}

/**
 * @param {number} userId
 * @param {() => any} fn
 */
export async function withUser(userId, fn) {
    const { env } = MockServer;
    const currentUser = env.user;
    const [targetUser] = /** @type {any} */ (env["res.users"]).browse(userId, {
        active_test: false,
    });
    authenticateUser(targetUser);
    let result;
    try {
        result = await fn();
    } finally {
        if (currentUser) {
            authenticateUser(currentUser);
        } else {
            logout();
        }
    }
    return result;
}

export const S_MODEL_LOADED = Symbol("model-loaded");
