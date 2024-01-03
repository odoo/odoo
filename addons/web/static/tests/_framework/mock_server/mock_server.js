/** @odoo-module */

import { after, before, globals, registerDebugInfo } from "@odoo/hoot";
import { mockFetch, mockWebSocket } from "@odoo/hoot-mock";
import { assets } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { fetchModelDefinitions } from "../module_set.hoot";
import { patchWithCleanup } from "../patch_test_helpers";
import { DEFAULT_FIELD_VALUES } from "./mock_fields";
import {
    FIELD_NOT_FOUND,
    MockServerError,
    getRecordQualifier,
    safeSplit,
} from "./mock_server_utils";

const { fetch: realFetch } = globals;

/**
 * @typedef {Record<string, any>} ActionDefinition
 *
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 *
 * @typedef {import("./mock_fields").FieldDefinition} FieldDefinition
 *
 * @typedef {MockServerBaseEnvironment & { [modelName: string]: Model }} MockServerEnvironment
 *
 * @typedef {import("./mock_model").Model} Model
 *
 * @typedef {import("./mock_model").ModelConstructor} ModelConstructor
 *
 * @typedef {(route: string, params: OrmParams) => any} OrmCallback
 *
 * @typedef {{
 *  args: any[];
 *  kwargs: KwArgs;
 *  method: string;
 *  model: string;
 * }} OrmParams
 *
 * @typedef {{ pure?: boolean }} RpcOptions
 *
 * @typedef {{
 *  lang_parameters?: Partial<typeof MockServer["prototype"]["lang_parameters"]>;
 *  models?: Iterable<ModelConstructor>;
 *  modules?: Partial<typeof MockServer["prototype"]["modules"]>;
 *  multi_lang?: typeof MockServer["prototype"]["multi_lang"];
 *  routes?: typeof MockServer["prototype"]["routes"];
 *  translations?: Record<string, string>;
 * }} ServerParams
 */

/**
 * @template [T={}]
 * @typedef {{
 *  args?: any[];
 *  context?: Record<string, any>;
 *  [key: string]: any;
 * } & Partial<T>} KwArgs
 */

/**
 * @template [T={}]
 * @typedef {(this: MockServer, request: Request, params: T) => any} RouteCallback
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {import("./mock_model").ModelRecord} user
 */
const authenticateUser = (user) => {
    const { env } = MockServer;
    if (!user?.id) {
        throw new MockServerError("Unauthorized");
    }
    env.cookie.set("sid", user.id);
};

/**
 * @param {string} modelName
 */
const modelNotFoundError = (modelName, consequence) => {
    let message = `cannot find a definition for model "${modelName}"`;
    if (consequence) {
        message += `: ${consequence}`;
    }
    message += ` (did you forget to use \`defineModels()?\`)`;
    return new MockServerError(message);
};

/**
 * @param {unknown} value
 */
const toDisplayName = (value) => {
    const str = String(value)
        .trim()
        .replace(/_id(s)?$/i, "$1")
        .replace(/([a-z])([A-Z])/g, (_, a, b) => `${a} ${b.toLowerCase()}`)
        .replace(/_/g, " ");
    return str[0].toUpperCase() + str.slice(1);
};

class MockServerBaseEnvironment {
    cookie = new Map();

    get companies() {
        const ids = Object.keys(session.user_companies.allowed_companies);
        return this.server.env["res.company"].read(ids);
    }

    get company() {
        return this.server.env["res.company"].read(session.user_companies.current_company)[0];
    }

    get context() {
        return session.user_context;
    }

    get lang() {
        return this.context.lang;
    }

    get uid() {
        return session.uid;
    }

    get user() {
        return this.server.env["res.users"].read(this.uid)[0];
    }

    // Note: the following getters do not exist in the actual server environment
    get partner() {
        return this.server.env["res.partner"].read(this.partner_id)[0];
    }

    get partner_id() {
        return session.partner_id;
    }

    /**
     * @param {MockServer} server
     */
    constructor(server) {
        this.server = server;
    }
}

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockServer {
    /** @type {MockServer | null} */
    static current = null;
    /** @type {MockServerEnvironment | null} */
    static models = [];
    static rpcListeners = [];

    static get env() {
        return this.current?.env;
    }

    // Server params
    lang_parameters = {
        date_format: "%d/%m/%Y",
        decimal_point: ".",
        direction: "ltr",
        grouping: "[3,0]",
        time_format: "%H:%M:%S",
        thousands_sep: ",",
        week_start: 7,
    };
    menus = {
        root: { id: "root", children: [1], name: "root", appID: "root" },
        1: { id: 1, children: [], name: "App0", appID: 1 },
    };
    modules = { web: { messages: [] } };
    multi_lang = false;

    // Server env
    env = this.makeServerEnv();

    // Data
    /** @type {Record<string, ActionDefinition>} */
    actions = {};
    /** @type {Record<string, Model>} */
    models = {};
    /** @type {ModelConstructor[]} */
    modelSpecs = [];
    /** @type {Set<string>} */
    modelNamesToFetch = new Set();

    // Routes
    /** @type {Record<string, [RegExp, string[], RouteCallback]>} */
    routes = {};
    started = false;
    /** @type {Record<string, OrmCallback[]>} */
    ormListeners = { "*": [] };

    // WebSocket connections
    /** @type {import("@odoo/hoot-mock").ServerWebSocket[]} */
    websockets = [];

    /**
     * Current request
     * @type {Request | null}
     */
    currentRequest = null;

    get currentRoute() {
        if (!this.currentRequest) {
            throw new MockServerError(`no current request`);
        }
        return new URL(this.currentRequest.url).pathname;
    }

    /**
     * @param {ServerParams} [params]
     */
    constructor(params) {
        if (MockServer.current) {
            throw new MockServerError(
                `cannot instantiate a new MockServer: one is already running`
            );
        }
        MockServer.current = this;

        // Set default routes
        this.onRpc("/web/action/load", this.mockActionLoad);
        this.onRpc("/web/bundle", this.mockBundle, { pure: true });
        this.onRpc("/web/dataset/call_kw", this.mockCallKw);
        this.onRpc("/web/dataset/resequence", this.mockResequence);
        this.onRpc("/web/image/:model/:id/:field", this.mockImage, { pure: true });
        this.onRpc("/web/webclient/load_menus", this.mockLoadMenus, { pure: true });
        this.onRpc("/web/webclient/translations", this.mockLoadTranslations, { pure: true });
        // Register "mock_rpc" registry items
        for (const [rpcRoute, rpcFn] of registry.category("mock_rpc").getEntries()) {
            if (typeof rpcFn === "function") {
                this.onRpc(rpcRoute, rpcFn);
            }
        }

        this.configure(params);

        for (const [method, callback] of MockServer.rpcListeners) {
            this.onRpc(method, callback);
        }

        const { loadCSS, loadJS } = assets;
        patchWithCleanup(assets, {
            loadJS: async (url) => {
                if (url.startsWith("/web/static/lib")) {
                    // Bypass `onRpc` for libs
                    return loadJS(url);
                }
                const res = await this.handle(url, {});
                if (!res.ok) {
                    return loadJS(url);
                }
                return res;
            },
            loadCSS: async (url) => {
                const res = await this.handle(url, {});
                if (!res.ok) {
                    return loadCSS(url);
                }
                return res;
            },
        });

        const restoreFetch = mockFetch((input, init) => this.handle(input, init));
        const restoreWebSocket = mockWebSocket((ws) => this.websockets.push(ws));

        after(() => {
            MockServer.current = null;

            restoreFetch();
            restoreWebSocket();
        });
    }

    /**
     * @param {OrmParams} params
     */
    callOrm(params) {
        const { method, model: modelName } = params;
        const args = params.args || [];
        const kwargs = params.kwargs || {};

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
            for (const parentName of model._inherit) {
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

        throw new MockServerError(`unimplemented server route: ${this.currentRoute}`);
    }

    /**
     * @param {Partial<ServerParams>} [params]
     */
    configure(params) {
        Object.assign(this.lang_parameters, params?.lang_parameters);
        Object.assign(this.modules, params?.modules);

        if (params?.multi_lang) {
            this.multi_lang = params.multi_lang;
        }

        if (params?.translations) {
            this.modules.web ||= {};
            this.modules.web.messages = Object.entries(params.translations).map(([id, string]) => ({
                id,
                string,
            }));
        }

        this.registerModels([...MockServer.models, ...(params?.models || [])]);

        for (const [route, callback] of Object.entries(params?.routes || {})) {
            this.onRpc(route, callback);
        }

        return this;
    }

    /**
     * @param {string} route
     * @returns {[RouteCallback, Record<string, string>]}
     */
    findRoute(route) {
        // Look in own routes
        for (const [, [regex, params, options, fn]] of Object.entries(this.routes)) {
            const match = route.match(regex);
            if (match) {
                const routeParams = {};
                for (let i = 0; i < params.length; i++) {
                    routeParams[params[i]] = match[i + 1];
                }
                return [fn, routeParams, options || {}];
            }
        }
        return [null, {}, {}];
    }

    generateRecords() {
        for (const model of Object.values(this.models)) {
            const seenIds = new Set();
            for (const record of model) {
                // Check for unknown fields
                for (const fieldName in record) {
                    if (!(fieldName in model._fields)) {
                        throw new MockServerError(
                            `unknown field "${fieldName}" on ${getRecordQualifier(
                                record
                            )} in model "${model._name}"`
                        );
                    }
                }
                // Apply values and default values
                for (const [fieldName, fieldDef] of Object.entries(model._fields)) {
                    if (fieldName === "id") {
                        record[fieldName] ||= model._getNextId();
                        continue;
                    }
                    if ("default" in fieldDef) {
                        const def = fieldDef.default;
                        record[fieldName] ??=
                            typeof def === "function" ? def.call(this, record) : def;
                    }
                    record[fieldName] ??= DEFAULT_FIELD_VALUES[fieldDef.type]();
                }
                if (seenIds.has(record.id)) {
                    throw new MockServerError(
                        `duplicate ID ${record.id} in model "${model._name}"`
                    );
                }
                seenIds.add(record.id);
            }
        }

        // creation of the ir.model.fields records, required for tracked fields
        const IrModelFields = this.models["ir.model.fields"];
        if (IrModelFields) {
            for (const model of Object.values(this.models)) {
                for (const [fieldName, field] of Object.entries(model._fields)) {
                    if (field.tracking) {
                        IrModelFields.create({
                            model: model._name,
                            name: fieldName,
                            ttype: field.type,
                        });
                    }
                }
            }
        }

        Object.values(this.models).forEach((model) => model._applyComputesAndValidate());
    }

    /**
     * @param {ModelConstructor} ModelClass
     * @returns {Model}
     */
    getModelDefinition(ModelClass) {
        const model = ModelClass.definition;

        // Server model
        if (model._fetch) {
            this.modelNamesToFetch.add(model._name);
        }

        // Model fields
        for (const [fieldName, fieldGetter] of Object.entries(ModelClass._fields)) {
            const fieldGetterValue = fieldGetter();
            if (fieldGetterValue.name) {
                throw new MockServerError(
                    `cannot set the name of field "${fieldName}" from its definition: got "${fieldGetterValue.name}"`
                );
            }

            /** @type {FieldDefinition} */
            const fieldDef = {
                string: toDisplayName(fieldName),
                ...fieldGetterValue,
                name: fieldName,
            };

            // On change function
            const onChange = fieldDef.onChange;
            if (typeof onChange === "function") {
                model._onChanges[fieldName] = onChange.bind(model);
            }

            model._fields[fieldName] = fieldDef;
        }

        return model;
    }

    /**
     * @param {string} [url]
     */
    getWebSockets(url) {
        return url ? this.websockets.filter((ws) => ws.url.includes(url)) : this.websockets;
    }

    /**
     * @param {string} url
     * @param {RequestInit} init
     * @param {RpcOptions} [options]
     */
    async handle(url, init, options = {}) {
        if (!this.started) {
            throw new MockServerError(
                `cannot handle \`fetch\`: server has not been started (did you forget to call \`start()\`?)`
            );
        }

        const method = init?.method?.toUpperCase() || (init?.body ? "POST" : "GET");
        this.currentRequest = new Request(url, { method, ...(init || {}) });

        const [routeFn, routeParams, routeOptions] = this.findRoute(this.currentRoute);
        const pure = options.pure || routeOptions.pure;
        if (!routeFn) {
            const message = `unimplemented server route: ${this.currentRoute}`;
            const body = pure
                ? "not found"
                : JSON.stringify({
                      error: {
                          code: 404,
                          data: { name: "not found" },
                          message,
                      },
                      result: null,
                  });
            return new Response(body, { status: 404 });
        }

        const result = await routeFn.call(this, this.currentRequest, routeParams);

        this.currentRequest = null;

        if (pure) {
            return result;
        }
        if (result instanceof Error) {
            return {
                result: null,
                error: {
                    code: 418,
                    data: result,
                    message: result.message,
                    type: result.name,
                },
            };
        } else {
            return { result, error: null };
        }
    }

    /**
     * @param {Iterable<Model>} models
     */
    async loadModels(models) {
        if (this.modelNamesToFetch.size) {
            const modelEntries = await fetchModelDefinitions(this.modelNamesToFetch);
            this.modelNamesToFetch.clear();

            for (const [
                name,
                { description, fields, inherit, order, parent_name, rec_name },
            ] of modelEntries) {
                const localModelDef = [...models].find((model) => model._name === name);
                localModelDef._description = description;
                localModelDef._inherit = inherit;
                localModelDef._order = order;
                localModelDef._parent_name = parent_name;
                localModelDef._rec_name = rec_name;
                for (const [fieldName, serverFieldDef] of Object.entries(fields)) {
                    localModelDef._fields[fieldName] = {
                        ...serverFieldDef,
                        ...localModelDef._fields[fieldName],
                    };
                }
            }
        }

        // Register models on mock server instance
        for (const model of models) {
            // Validate _rec_name
            if (model._rec_name) {
                if (!(model._rec_name in model._fields)) {
                    throw new MockServerError(
                        `invalid _rec_name "${model._rec_name}" on model "${model._name}": field does not exist`
                    );
                }
            } else if ("name" in model._fields) {
                model._rec_name = "name";
            } else if ("x_name" in model._fields) {
                model._rec_name = "x_name";
            }

            this.models[model._name] = model;
        }

        // Inheritance
        for (const model of models) {
            // Apply inherited fields
            for (const modelName of safeSplit(model._inherit)) {
                if (!modelName) {
                    continue;
                }
                const parentModel = this.models[modelName];
                if (!parentModel) {
                    throw modelNotFoundError(modelName, "could not inherit from model");
                }
                for (const fieldName in parentModel._fields) {
                    model._fields[fieldName] ??= parentModel._fields[fieldName];
                }
            }

            // Check missing models
            for (const field of Object.values(model._fields)) {
                if (field.relation && !this.models[field.relation]) {
                    throw modelNotFoundError(field.relation, "could not find model");
                }
            }
        }

        // Compute functions
        for (const model of models) {
            for (const field of Object.values(model._fields)) {
                /** @type {(this: Model) => void} */
                let computeFn = field.compute;
                if (typeof computeFn === "string") {
                    if (typeof model[computeFn] !== "function") {
                        throw new MockServerError(
                            `could not find compute function "${computeFn}" on model "${model._name}"`
                        );
                    }
                    computeFn = model[computeFn];
                } else if (field.related) {
                    const relatedFieldName = field.name;
                    const fieldNames = safeSplit(field.related, ".");
                    computeFn = function () {
                        for (const record of this) {
                            const relatedValue = this._followRelation(record, fieldNames);
                            if (relatedValue === FIELD_NOT_FOUND) {
                                // The related field is not found on the record, so we
                                // remove the compute function.
                                model._computes.delete(computeFn);
                                return;
                            } else {
                                record[relatedFieldName] = relatedValue;
                            }
                        }
                    };
                }
                if (typeof computeFn === "function") {
                    model._computes.add(computeFn);
                }
            }
        }
    }

    /**
     * @returns {MockServerEnvironment}
     */
    makeServerEnv() {
        const serverEnv = new MockServerBaseEnvironment(this);
        return new Proxy(serverEnv, {
            get: (target, p) => {
                if (p in target || typeof p !== "string") {
                    return target[p];
                }
                const model = this.models[p];
                if (!model) {
                    throw modelNotFoundError(p, "could not get model from server environment");
                }
                return model;
            },
        });
    }

    /**
     * @param {string} [method]
     * @param {OrmCallback} callback
     */
    onOrmMethod(method, callback) {
        if (typeof method === "function") {
            callback = method;
            method = "*";
        } else if (!method) {
            method = "*";
        }
        if (!this.ormListeners[method]) {
            this.ormListeners[method] = [];
        }
        this.ormListeners[method].push(callback);
    }

    /**
     * @param {`/${string}`} route
     * @param {RouteCallback} callback
     * @param {RpcOptions} options
     */
    onRoute(route, callback, options) {
        const routeParams = [];
        const routeRegex = new RegExp(
            `^${route.replace("*", ".*").replace(/:([^/]+)/g, (_, param) => {
                routeParams.push(param);
                return `([^/]+)`;
            })}`,
            "i"
        );
        const routeItem = [routeRegex, routeParams, options, callback];

        // Route already exists: replace it
        if (this.routes[route]) {
            this.routes[route] = routeItem;
            return;
        }

        // Sort routes by length descending
        const entries = Object.entries(this.routes);
        let inserted = false;
        for (let i = 0; i < entries.length; i++) {
            const [entryRoute] = entries[i];
            if (route.length >= entryRoute.length) {
                entries.splice(i, 0, [route, routeItem]);
                inserted = true;
                break;
            }
        }
        if (!inserted) {
            entries.push([route, routeItem]);
        }
        this.routes = Object.fromEntries(entries);
    }

    /**
     * @param {string} route
     * @param {OrmCallback | RouteCallback} callback
     * @param {RpcOptions} options
     */
    onRpc(route, callback, options) {
        if (typeof route === "string" && route.startsWith("/")) {
            this.onRoute(route, callback, options);
        } else {
            this.onOrmMethod(route, callback);
        }
        return this;
    }

    /**
     * @param {Iterable<ModelConstructor>} ModelClasses
     */
    registerModels(ModelClasses) {
        const newSpecs = [];
        for (const ModelClass of ModelClasses) {
            const model = this.getModelDefinition(ModelClass);
            newSpecs.push(model);
            this.modelSpecs.push(model);
        }
        return newSpecs;
    }

    async start() {
        if (this.started) {
            throw new MockServerError("MockServer has already been started");
        }
        this.started = true;

        await this.loadModels(this.modelSpecs);
        this.generateRecords();

        return this;
    }

    //-------------------------------------------------------------------------
    // Route methods
    //-------------------------------------------------------------------------

    /** @type {RouteCallback} */
    async mockActionLoad(request) {
        const { params } = await request.json();
        const action = this.actions[params.action_id];
        if (!action) {
            // when the action doesn't exist, the real server doesn't crash, it
            // simply returns false
            console.warn(`No action found for ID ${JSON.stringify(params.action_id)}`);
        }
        return action || false;
    }

    /** @type {RouteCallback} */
    async mockBundle(request) {
        // No mock here: we want to fetch the actual bundle
        return realFetch(request.url);
    }

    /** @type {RouteCallback} */
    async mockCallKw(request) {
        const { params } = await request.json();
        const route = this.currentRoute;

        let result;
        // Check own routes
        for (const fn of [...(this.ormListeners[params.method] || []), ...this.ormListeners["*"]]) {
            result ??= await fn.call(this, route, params);
            if (result !== undefined && result !== null) {
                break;
            }
        }
        // Check ORM methods
        try {
            result ??= await this.callOrm(params);
        } catch (error) {
            return error;
        }
        return result;
    }

    /** @type {RouteCallback} */
    async mockImage(request, { model, field, id }) {
        return `<fake url to record ${id} on ${model}.${field}>`;
    }

    /** @type {RouteCallback} */
    async mockLoadMenus() {
        return this.menus;
    }

    /** @type {RouteCallback} */
    async mockLoadTranslations() {
        return {
            lang_parameters: this.lang_parameters,
            modules: this.modules,
            multi_lang: this.multi_lang,
        };
    }

    /** @type {RouteCallback} */
    async mockResequence(request) {
        const { params } = request.json();
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
export async function authenticate(login, password) {
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
 * Registers a list of model classes on the current/future {@link MockServer} instance.
 *
 * @param  {ModelConstructor[] | Record<string, ModelConstructor>} ModelClasses
 */
export function defineModels(ModelClasses) {
    const classes = Object.values(ModelClasses);

    before(() => {
        const originalModels = [...MockServer.models];
        MockServer.models = [...MockServer.models, ...classes];
        return () => (MockServer.models = originalModels);
    });

    if (MockServer.current) {
        const specs = MockServer.current.registerModels(classes);
        if (MockServer.current.started) {
            MockServer.current.loadModels(specs);
        }
    }

    return ModelClasses;
}

/**
 * @type {typeof MockServer["prototype"]["getWebSockets"]}
 */
export function getServerWebSockets(url) {
    if (!MockServer.current) {
        throw new MockServerError(`cannot get websockets: no MockServer is currently running`);
    }
    return MockServer.current.getWebSockets(url);
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
    const [publicUser] = env["res.users"]._filter([["id", "=", this.publicUserId]], {
        active_test: false,
    });
    authenticate(publicUser.login, publicUser.password);
}

/**
 * Shortcut function to create and start a {@link MockServer}.
 *
 * @param {ServerParams} params
 */
export async function makeMockServer(params) {
    const server = new MockServer(params);

    registerDebugInfo(server);

    return server.start();
}

/**
 * Registers an RPC handler on the current/future {@link MockServer} instance.
 *
 * @type {typeof MockServer["prototype"]["onRpc"]}
 */
export function onRpc(method, callback, options) {
    before(() => {
        const originalListeners = [...MockServer.rpcListeners];
        MockServer.rpcListeners = [...MockServer.rpcListeners, [method, callback, options]];
        return () => (MockServer.rpcListeners = originalListeners);
    });

    if (MockServer.current) {
        MockServer.current.onRpc(method, callback, options);
    }
}

/**
 * Executes the given callback as the given user, then restores the previous user.
 *
 * @param {number} userId
 * @param {() => any} fn
 */
export async function withUser(userId, fn) {
    const { env } = MockServer;
    const user = env.user;
    const [targetUser] = env["res.users"]._filter([["id", "=", userId]], { active_test: false });
    authenticateUser(targetUser);
    let result;
    try {
        result = await fn();
    } finally {
        if (user) {
            authenticateUser(user);
        } else {
            logout();
        }
    }
    return result;
}
