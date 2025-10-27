import {
    after,
    before,
    createJobScopedGetter,
    expect,
    getCurrent,
    mockFetch,
    mockWebSocket,
    registerDebugInfo,
} from "@odoo/hoot";
import { makeErrorFromResponse, rpc, RPCError } from "@web/core/network/rpc";
import { ensureArray, isIterable } from "@web/core/utils/arrays";
import { isObject } from "@web/core/utils/objects";
import { RPCCache } from "@web/core/network/rpc_cache";
import { hashCode } from "@web/core/utils/strings";
import { serverState } from "../mock_server_state.hoot";
import { fetchModelDefinitions, globalCachedFetch, registerModelToFetch } from "../module_set.hoot";
import { DEFAULT_FIELD_PROPERTIES, getFieldDisplayName, S_SERVER_FIELD } from "./mock_fields";
import {
    getRecordQualifier,
    makeKwArgs,
    makeServerError,
    MockServerError,
    safeSplit,
} from "./mock_server_utils";

const { DateTime } = luxon;

/**
 * @typedef {{
 *  type: string;
 *  [key: string]: any;
 * }} ActionDefinition
 *
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 *
 * @typedef {import("./mock_fields").FieldDefinition} FieldDefinition
 *
 * @typedef {{
 *  actionID?: string | number;
 *  appID?: MenuId;
 *  children?: (MenuId | MenuDefinition)[];
 *  id: MenuId;
 *  name: string;
 *  xmlid?: string;
 * }} MenuDefinition
 *
 * @typedef {number | "root"} MenuId
 *
 * @typedef {MockServerBaseEnvironment & { [modelName: string]: Model }} MockServerEnvironment
 *
 * @typedef {import("./mock_model").Model} Model
 *
 * @typedef {import("./mock_model").ModelConstructor} ModelConstructor
 *
 * @typedef {(this: MockServer, params: OrmParams) => unknown} OrmCallback
 *
 * @typedef {{
 *  args: any[];
 *  kwargs: KwArgs;
 *  method: string;
 *  model: string;
 *  parent: () => any;
 *  request: Request;
 *  route: string;
 * }} OrmParams
 *
 * @typedef {[RegExp, Record<string, string>]} RouteMatcher
 *
 * @typedef {{
 *  final?: boolean;
 *  pure?: boolean;
 * }} RouteOptions
 *
 * @typedef {`/${string}`} RoutePath
 *
 * @typedef {{
 *  actions?: Partial<MockServer["actions"]>;
 *  lang?: string;
 *  lang_parameters?: Partial<MockServer["_lang_parameters"]>;
 *  menus?: MenuDefinition[];
 *  models?: Iterable<ModelConstructor>;
 *  modules?: Partial<MockServer["_modules"]>;
 *  multi_lang?: import("../mock_server_state.hoot").ServerState["multiLang"];
 *  routes?: Parameters<MockServer["_onRpc"]>;
 *  timezone?: string;
 *  translations?: Record<string, string>;
 * }} ServerParams
 *
 * @typedef {import("@odoo/hoot").ServerWebSocket} ServerWebSocket
 *
 * @typedef {string | Iterable<string> | RegExp} StringMatcher
 *
 * @typedef {(string | RegExp)[]} StringMatchers
 */

/**
 * @template T
 * @typedef {{ mode?: "add" | "replace" = T; }} DefineOptions
 */

/**
 * @template [T={}]
 * @typedef {import("./mock_model").KwArgs} KwArgs
 */

/**
 * @template [T=string]
 * @typedef {(this: MockServer, request: Request, params: Record<T, string>) => any} RouteCallback
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {import("./mock_model").ModelRecord} user
 */
function authenticateUser(user) {
    const { env } = MockServer;
    if (!user?.id) {
        throw new MockServerError("Unauthorized");
    }
    env.cookie.set("sid", user.id);
    env.uid = user.id;
}

/**
 * @template T
 * @param {T} object
 * @return {T}
 */
function deepCopy(object) {
    if (!object) {
        return object;
    }
    if (typeof object === "object") {
        if (object?.nodeType) {
            // Nodes
            return object.cloneNode(true);
        } else if (object instanceof Date || object instanceof DateTime) {
            // Dates
            return new object.constructor(object);
        } else if (isIterable(object)) {
            // Iterables
            const copy = [...object].map(deepCopy);
            if (object instanceof Set || object instanceof Map) {
                return new object.constructor(copy);
            } else {
                return copy;
            }
        } else {
            // Other objects
            return Object.fromEntries(
                Object.entries(object).map(([key, object]) => [key, deepCopy(object)])
            );
        }
    }
    return object;
}

/**
 * @param {DefineOptions<"replace">} [options]
 */
function getAssignAction(options) {
    const shouldAdd = options?.mode === "add";
    return function assign(target, key, value) {
        if (shouldAdd && target[key] === Object(target[key])) {
            // Add value
            if (Array.isArray(target[key])) {
                target[key].push(...value);
            } else {
                Object.assign(target[key], value);
            }
        } else {
            // Replace value
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

/**
 * @param {RequestInit} init
 */
function getJsonRpcParams({ headers, body }) {
    if (headers.get("Content-Type") !== "application/json" || typeof body !== "string") {
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
 * @param {MockServer["_models"]}
 * @returns {MockServerEnvironment}
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
                throw modelNotFoundError(p, "could not get model from server environment");
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
            (matcher instanceof RegExp ? matcher.test(target) : target === matcher)
    );
}

/**
 * @param {string} modelName
 */
function modelNotFoundError(modelName, consequence) {
    return new MockServerError(
        `Cannot find a definition for model "${modelName}": ${consequence} (did you forget to use \`defineModels()?\`)`
    );
}

/**
 * @param {Record<string, string> | Iterable<{ id: string, string: string }>} translations
 */
function parseTranslations(translations) {
    return isIterable(translations)
        ? translations
        : Object.entries(translations).map(([id, string]) => ({ id, string }));
}

/**
 * @param {ServerParams} params
 * @param {DefineOptions<"replace">} [options]
 */
function _defineParams(params, options) {
    const assign = getAssignAction(options);
    const currentParams = getCurrentParams();
    for (const [key, value] of Object.entries(params)) {
        assign(currentParams, key, value);
    }
    return MockServer.current?.configure(params);
}

const getCurrentParams = createJobScopedGetter(
    /**
     * @param {ServerParams} previous
     */
    function getCurrentParams(previous) {
        return {
            ...previous,
            actions: deepCopy(previous?.actions || []),
            menus: deepCopy(previous?.menus || [DEFAULT_MENU]),
            models: [...(previous?.models || [])], // own instance getters, no need to deep copy
            routes: [...(previous?.routes || [])],
        };
    }
);

class MockServerBaseEnvironment {
    cookie = new Map();

    get companies() {
        return MockServer.env["res.company"].read(serverState.companies.map((c) => c.id));
    }

    get company() {
        return this.companies[0];
    }

    /**
     * @type {import("@web/core/context").Context}
     */
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

const R_DATASET_ROUTE = /\/web\/dataset\/call_(button|kw)\/[\w.-]+\/(?<step>\w+)/;
const R_ROUTE_PARAM = /<((?<type>\w+):)?(?<name>[\w-]+)>/g;
const R_WILDCARD = /\*+/g;
const R_WEBCLIENT_ROUTE = /(?<step>\/web\/webclient\/\w+)/;

/** @type {WeakMap<() => any, MockServer>} */
const mockServers = new WeakMap();
/** @type {WeakSet<typeof Model>} */
const seenModels = new WeakSet();

let nextJsonRpcId = 1e9;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

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

    // Server parameters (private)

    /**
     * @private
     */
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
    /**
     * @private
     */
    _modules = {
        web: { messages: [] },
    };
    /**
     * @private
     * @type {[StringMatchers, StringMatchers, OrmCallback][]>}
     */
    _ormListeners = [];
    /**
     * @private
     * @type {[RegExp[], RouteCallback, RouteOptions][]}
     */
    _routes = [];
    /**
     * @private
     */
    _started = false;
    /**
     * WebSocket connections
     * @private
     * @type {ServerWebSocket[]}
     */
    _websockets = [];

    // Server environment (needs '_models' to be initialized first)
    env = makeServerEnv(this._models);

    /**
     * @param {Partial<ServerParams>} params
     * @param {DefineOptions<"replace">} [options]
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
            // Never fully replace "lang_parameters"
            Object.assign(this._lang_parameters, params.lang_parameters);
        }
        if (params.menus) {
            assign(this, "menus", params.menus);
        }
        if (params.models) {
            assign(
                this,
                "_modelSpecs",
                [...params.models].map((ModelClass) => this._getModelDefinition(ModelClass))
            );
            if (this._started) {
                await this._loadModels();
            }
        }
        if (params.modules) {
            for (const [module, values] in Object.entries(params.modules)) {
                this._modules[module] ||= { messages: [] };
                assign(
                    this._modules[module],
                    "messages",
                    parseTranslations(values.message || values)
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
            assign(this._modules.web, "messages", parseTranslations(params.translations));
        }
        if (params.routes) {
            for (const args of params.routes) {
                this._onRpc(...args);
            }
        }

        return this;
    }

    /**
     * @param {string} [url]
     */
    getWebSockets(url) {
        return url ? this._websockets.filter((ws) => ws.url.includes(url)) : this._websockets;
    }

    async start() {
        if (this._started) {
            throw new MockServerError("MockServer has already been _started");
        }
        this._started = true;

        registerDebugInfo("mock server", this);

        // Add RPC cache
        rpc.setCache(new RPCCache("mockRpc", 1, "23aeb0ff5d46cfa8aa44163720d871ac"));
        after(() => rpc.setCache(null));

        // Intercept all server calls
        mockFetch(this._handleRequest.bind(this));
        mockWebSocket(this._handleWebSocket.bind(this));

        // Set default routes
        this._onRoute(["/web/action/load"], this.loadAction);
        this._onRoute(["/web/action/load_breadcrumbs"], this.loadActionBreadcrumbs);
        this._onRoute(["/web/bundle/<string:bundle_name>"], this.loadBundle);
        this._onRoute(["/web/dataset/call_kw", "/web/dataset/call_kw/<path:path>"], this.callKw, {
            final: true,
        });
        this._onRoute(
            ["/web/dataset/call_button", "/web/dataset/call_button/<path:path>"],
            this.callKw,
            { final: true }
        );
        this._onRoute(["/web/dataset/resequence"], this.resequence);
        this._onRoute(["/web/image/<string:model>/<int:id>/<string:field>"], this.loadImage);
        this._onRoute(["/web/webclient/load_menus"], this.loadMenus);
        this._onRoute(["/web/webclient/translations"], this.loadTranslations);

        // Register ambiant parameters
        await this.configure(getCurrentParams());

        return this;
    }

    //-------------------------------------------------------------------------
    // Private methods
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {OrmParams} params
     */
    _callOrm(params) {
        const { args, method, model: modelName, kwargs } = params;

        // Try to find a model method
        if (modelName) {
            const model = this.env[modelName];
            if (typeof model[method] === "function") {
                const expectedLength = model[method].length;
                while (args.length < expectedLength) {
                    args.push(undefined);
                }
                return model[method](...args, kwargs);
            }

            // Try to find a parent model method
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
     * @param {string} route
     */
    _findRouteListeners(route) {
        /** @type {[RouteCallback, Record<string, string>, RouteOptions][]} */
        const listeners = [];
        for (const [routeRegexes, callback, options] of this._routes) {
            for (const regex of routeRegexes) {
                const argsMatch = route.match(regex);
                if (argsMatch) {
                    listeners.unshift([callback, argsMatch.groups, options]);
                }
            }
        }
        return listeners;
    }

    /**
     * @private
     * @param {Partial<ActionDefinition>} rawAction
     */
    _getAction(rawAction) {
        const mainIdentifier = ACTION_IDENTIFIERS.find((identifier) => rawAction[identifier]);
        const id = rawAction[mainIdentifier];
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
                // Embedded actions are treated as regular actions for simplicity's sake
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
                        action.embedded_action_ids.push(this._getAction(embeddedAction));
                    }
                }
                break;
            }
            default: {
                if (!(action.type in ACTION_TYPES)) {
                    throw new MockServerError(
                        `Invalid action type "${action.type}" in action ${id}`
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

        // Server model
        if (ModelClass._fetch) {
            this._modelNamesToFetch.add(model._name);
        }

        return model;
    }

    /**
     * @private
     * @param {string} url
     * @param {RequestInit} init
     */
    async _handleRequest(url, init) {
        const request = new Request(url, init);
        const route = new URL(request.url).pathname;
        let jsonRpcParams = getJsonRpcParams(init);
        let error = null;
        let result = null;

        const listeners = this._findRouteListeners(route);
        if (!listeners.length) {
            error = new MockServerError(`Unimplemented server route: ${route}`);
        } else {
            for (const [callback, routeParams, { final, pure }] of listeners) {
                try {
                    const callbackResult = await callback.call(this, request, routeParams);
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

        // We have several scenarios at this point:
        //
        // - either the request is considered to be a JSON-RPC:
        //  -> the response is formatted accordingly (i.e. { error, result })
        //
        // - in other cases:
        //  -> the response is returned or thrown as-is.
        if (jsonRpcParams) {
            if (error) {
                if (error instanceof RPCError) {
                    jsonRpcParams.error = { ...error };
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
                jsonRpcParams.result = result;
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

    /**
     * @private
     */
    async _loadModels() {
        const models = this._modelSpecs;
        const serverModelInheritances = new Set();
        this._modelSpecs = [];

        let serverModels = {};
        if (this._modelNamesToFetch.size) {
            serverModels = await fetchModelDefinitions(this._modelNamesToFetch);
            this._modelNamesToFetch.clear();
        }

        // First iteration: set own properties and fields for each model
        for (const model of models) {
            // Server model properties
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

                // Server properties
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

                // '_inherit' property
                if (inherit?.length) {
                    const inheritList = new Set(safeSplit(model._inherit));
                    for (const inherittedModelName of inherit) {
                        inheritList.add(inherittedModelName);
                        serverModelInheritances.add([model._name, inherittedModelName].join(","));
                    }
                    model._inherit = [...inheritList].join(",");
                }

                // Fields (lowest priority): server fields definitions
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

            // Validate _rec_name
            if (model._rec_name) {
                if (!(model._rec_name in model._fields)) {
                    throw new MockServerError(
                        `Invalid _rec_name "${model._rec_name}" on model "${model._name}": field does not exist`
                    );
                }
            } else if ("name" in model._fields) {
                model._rec_name = "name";
            } else if ("x_name" in model._fields) {
                model._rec_name = "x_name";
            }

            // Find duplicate models
            if (model._name in this._models) {
                const existingModel = this._models[model._name];
                // Add fields added from parent, since public class instance fields
                // are not included in the prototype.
                for (const fieldName in existingModel._fields) {
                    model._fields[fieldName] ??= existingModel._fields[fieldName];
                }
                Object.setPrototypeOf(Object.getPrototypeOf(model), existingModel);
            } else if (model._name in this.env) {
                throw new MockServerError(
                    `Cannot register model "${model._name}": a server environment property with the same name already exists`
                );
            }

            // Register models on mock server
            this._models[model._name] = model;
        }

        // Second iteration: model inheritance +
        for (const model of models) {
            // Apply inherited fields
            for (const modelName of safeSplit(model._inherit)) {
                if (!modelName) {
                    continue;
                }
                const parentModel = this._models[modelName];
                if (parentModel) {
                    for (const fieldName in parentModel._fields) {
                        model._fields[fieldName] ??= parentModel._fields[fieldName];
                    }
                } else if (serverModelInheritances.has([model._name, modelName].join(","))) {
                    // Inheritance comes from the server, so we can safely remove it:
                    // it means that the inherited model has not been fetched in this
                    // context.
                    model._inherit = model._inherit.replace(new RegExp(`${modelName},?`), "");
                } else {
                    throw modelNotFoundError(modelName, "could not inherit from model");
                }
            }

            // Re-iterate over fields after inheritances have been applied
            for (const [fieldName, field] of Object.entries(model._fields)) {
                // Check missing models
                if (field.relation && !this._models[field.relation]) {
                    if (field[S_SERVER_FIELD]) {
                        delete model._fields[fieldName];
                        continue;
                    } else {
                        throw modelNotFoundError(field.relation, "could not find model");
                    }
                }

                // Finalize field definitions
                field.name = fieldName;
                field.string ||= getFieldDisplayName(fieldName);

                // onChange
                const onChange = field.onChange;
                if (typeof onChange === "function") {
                    model._onChanges[fieldName] ||= onChange.bind(model);
                }

                // Computed & related fields
                if (field.compute) {
                    // Computed field
                    /** @type {(this: Model, fieldName: string) => void} */
                    let computeFn = field.compute;
                    if (typeof computeFn !== "function") {
                        computeFn = model[computeFn];
                        if (typeof computeFn !== "function") {
                            throw new MockServerError(
                                `Could not find compute function "${computeFn}" on model "${model._name}"`
                            );
                        }
                    }

                    model._computes[fieldName] = computeFn;
                } else if (field.related) {
                    // Related field
                    model._related.add(fieldName);
                }
            }

            // Generate initial records
            const recordsWithoutId = [];
            const seenIds = new Set();
            for (const record of model._records) {
                // Check for unknown fields
                for (const fieldName in record) {
                    if (!(fieldName in model._fields)) {
                        throw new MockServerError(
                            `Unknown field "${fieldName}" on ${getRecordQualifier(
                                record
                            )} in model "${model._name}"`
                        );
                    }
                }
                if (record.id) {
                    if (seenIds.has(record.id)) {
                        throw new MockServerError(
                            `Duplicate ID ${record.id} in model "${model._name}"`
                        );
                    }
                    seenIds.add(record.id);
                } else {
                    recordsWithoutId.push(record);
                }
                model.push(record);
            }
            model._records = [];

            // Records without ID are assigned later to avoid collisions
            for (const record of recordsWithoutId) {
                record.id = model._getNextId();
            }
        }

        // Third iteration: apply default values for each record. Can only be done
        // after each record has been created since some 'default' handlers should
        // return actual record IDs. Afterwards, the values for each record can be
        // validated.
        for (const model of models) {
            for (const record of model) {
                model._applyDefaults(record);
            }
            model._applyComputesAndValidate();
        }

        // creation of the ir.model.fields records, required for tracked fields
        const IrModelFields = this._models["ir.model.fields"];
        if (IrModelFields) {
            for (const model of models) {
                for (const field of Object.values(model._fields)) {
                    if (field.tracking) {
                        IrModelFields.create({
                            model: model._name,
                            name: field.name,
                            ttype: field.type,
                        });
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
    /**
     * @private
     * @param {StringMatchers | OrmCallback} model
     * @param {StringMatcher | OrmCallback} [method]
     * @param {OrmCallback} [callback]
     */
    _onOrmMethod(...args) {
        /** @type {OrmCallback[]} */
        const [callback] = ensureArray(args.pop());
        /** @type {StringMatchers} */
        const method = ensureArray(args.pop() || "*");
        /** @type {StringMatchers} */
        const model = ensureArray(args.pop() || "*");

        if (typeof callback !== "function") {
            throw new MockServerError(
                `onRpc: expected callback to be a function, got: ${callback}`
            );
        }

        this._ormListeners.push([model, method, callback]);
    }

    /**
     * @private
     * @param {RoutePath[]} routes
     * @param {RouteCallback} callback
     * @param {RouteOptions} options
     */
    _onRoute(routes, callback, options) {
        const routeRegexes = routes.map((route) => {
            const regexString = route
                // Replace parameters by regex notation and store their names
                .replaceAll(R_ROUTE_PARAM, (...args) => {
                    const { name, type } = args.pop();
                    return `(?<${name}>${ALLOWED_CHARS[type] || ALLOWED_CHARS.default}+)`;
                })
                // Replace glob wildcards by regex wildcard
                .replaceAll(R_WILDCARD, ".*");
            return new RegExp(`^${regexString}$`, "i");
        });

        this._routes.push([routeRegexes, callback, options || {}]);
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
    /**
     * @private
     * @param {StringMatcher | OrmCallback} route
     * @param {RouteCallback | StringMatcher | OrmCallback} [callback]
     * @param {RouteOptions | OrmCallback} [options]
     */
    _onRpc(...args) {
        const ormArgs = [];
        const routeArgs = [];
        for (const val of ensureArray(args.shift())) {
            if (typeof val === "string" && val.startsWith("/")) {
                routeArgs.push(val);
            } else {
                ormArgs.push(val);
            }
        }
        if (ormArgs.length) {
            this._onOrmMethod(ormArgs, ...args);
        }
        if (routeArgs.length) {
            this._onRoute(routeArgs, ...args);
        }
        return this;
    }

    //-------------------------------------------------------------------------
    // Route methods
    //-------------------------------------------------------------------------

    /**
     * @type {RouteCallback}
     */
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

    /**
     * @type {RouteCallback}
     */
    async loadAction(request) {
        const { params } = await request.json();
        return this._findAction(params.action_id);
    }

    /**
     * @type {RouteCallback}
     */
    async loadActionBreadcrumbs(request) {
        const { params } = await request.json();
        const { actions } = params;
        return actions.map(({ action: actionId, model, resId }) => {
            /** @type {string} */
            let displayName;
            if (actionId) {
                const action = this._findAction(actionId);
                if (resId) {
                    displayName = this.env[action.res_model].browse(resId)[0].display_name;
                } else {
                    displayName = action.name;
                }
            } else if (model) {
                if (!resId) {
                    throw new MockServerError("Actions with a 'model' should also have a 'resId'");
                }
                displayName = this.env[model].browse(resId)[0].display_name;
            } else {
                throw new MockServerError(
                    "Actions should have either an 'action' (ID or path) or a 'model'"
                );
            }
            return { display_name: displayName };
        });
    }

    /**
     * @type {RouteCallback<"bundle_name">}
     */
    async loadBundle(request) {
        // No mock here: we want to fetch the actual bundle (and cache it between suites),
        // although there is a protection to ensure a bundle doesn't leak to the
        // next test.
        const initiatorTestId = getCurrent().test?.id;
        if (initiatorTestId) {
            const result = await globalCachedFetch(request.url);
            if (initiatorTestId === getCurrent().test?.id) {
                return result;
            }
        }
        return new Promise(() => {});
    }

    /**
     * @type {RouteCallback<"model" | "field" | "id">}
     */
    async loadImage(request, { id, model, field }) {
        return `<fake url to record ${id} on ${model}.${field}>`;
    }

    /**
     * @type {RouteCallback<"unique">}
     */
    async loadMenus() {
        /** @type {MenuId[]} */
        const allChildIds = new Set();
        /** @type {Record<MenuId, MenuDefinition>} */
        const menuDict = {};
        /** @type {MenuDefinition[]} */
        const menuStack = [{ ...ROOT_MENU, children: this.menus }];
        while (menuStack.length) {
            const menu = menuStack.shift();
            /** @type {Set<MenuId>} */
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
            throw new MockServerError(`Missing menu ID(s): ${missingMenuIds.join(", ")}`);
        }
        return menuDict;
    }

    /**
     * @type {RouteCallback<"unique">}
     */
    async loadTranslations(request) {
        const requestHash = new URL(request.url).searchParams.get("hash");
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

        const currentHash = hashCode(JSON.stringify(result)).toString(16);
        if (currentHash === requestHash) {
            return {
                lang: serverState.lang,
                hash: currentHash,
                no_change: true,
            };
        }
        result.hash = currentHash;
        return result;
    }

    /**
     * @type {RouteCallback}
     */
    async resequence(request) {
        const { params } = await request.json();
        const offset = params.offset ? Number(params.offset) : 0;
        const field = params.field || "sequence";
        if (!(field in this.env[params.model]._fields)) {
            return false;
        }
        for (const index in params.ids) {
            const record = this.env[params.model].find((r) => r.id === params.ids[index]);
            record[field] = Number(index) + offset;
        }
        return true;
    }
}

/**
 * Authenticates a user on the mock server given its login and password.
 *
 * @param {string} login
 * @param {string} password
 */
export function authenticate(login, password) {
    const { env } = MockServer;
    const [user] = env["res.users"]._filter(
        [
            ["login", "=", login],
            ["password", "=", password],
        ],
        { active_test: false }
    );
    authenticateUser(user);
    env.cookie.set("authenticated_user_sid", env.cookie.get("sid"));
}

/**
 * @param {ActionDefinition[]} actions
 * @param {DefineOptions<"add">} [options]
 */
export function defineActions(actions, options) {
    before(() => _defineParams({ actions }, { mode: "add", ...options }));
}

/**
 * @param {MenuDefinition[]} menus
 * @param {DefineOptions<"add">} [options]
 */
export function defineMenus(menus, options) {
    before(() => _defineParams({ menus }, { mode: "add", ...options }));
}

/**
 * Registers a list of model classes on the current/future {@link MockServer} instance.
 *
 * @param  {ModelConstructor[] | Record<string, ModelConstructor>} ModelClasses
 * @param {DefineOptions<"add">} [options]
 */
export function defineModels(ModelClasses, options) {
    const models = Object.values(ModelClasses);
    for (const ModelClass of models) {
        if (seenModels.has(ModelClass)) {
            continue;
        }
        seenModels.add(ModelClass);
        // we cannot get the `definition` as this will trigger the model creation
        if (ModelClass._fetch) {
            registerModelToFetch(ModelClass.getModelName());
        }
    }
    before(() => _defineParams({ models }, { mode: "add", ...options }));
}

/**
 * @param {ServerParams} params
 * @param {DefineOptions<"replace">} [options]
 */
export function defineParams(params, options) {
    before(() => _defineParams(params, options));
}

/**
 * Logs out the current user (if any)
 */
export function logout() {
    const { env } = MockServer;
    if (env.cookie.get("authenticated_user_sid") === env.cookie.get("sid")) {
        env.cookie.delete("authenticated_user_sid");
    }
    env.cookie.delete("sid");
    const [publicUser] = env["res.users"].browse(serverState.publicUserId, {
        active_test: false,
    });
    authenticate(publicUser.login, publicUser.password);
}

/**
 * Shortcut function to create and start a {@link MockServer}.
 * @type {MockServer["start"]}
 */
export async function makeMockServer() {
    return getCurrentMockServer().start();
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
/**
 * Registers an RPC handler on the current/future {@link MockServer} instance.
 *
 * @type {MockServer["_onRpc"]}
 */
export function onRpc(...args) {
    before(() => _defineParams({ routes: [args] }, { mode: "add" }));
}

/**
 * calls expect.step for all network calls. Because of how the mock server
 * works, you need to call this *after* all your custom mockRPCs that return
 * something, otherwise the mock server will not call this function's handler.
 *
 * @returns {void}
 */
export function stepAllNetworkCalls() {
    onRpc("/*", (request) => {
        const route = new URL(request.url).pathname;
        let match = route.match(R_DATASET_ROUTE);
        if (match) {
            return void expect.step(match.groups?.step || route);
        }
        match = route.match(R_WEBCLIENT_ROUTE);
        if (match) {
            return void expect.step(match.groups?.step || route);
        }
        return void expect.step(route);
    });
}

/**
 * Executes the given callback as the given user, then restores the previous user.
 *
 * @param {number} userId
 * @param {() => any} fn
 */
export async function withUser(userId, fn) {
    const { env } = MockServer;
    const currentUser = env.user;
    const [targetUser] = env["res.users"].browse(userId, { active_test: false });
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
