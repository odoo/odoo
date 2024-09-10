import {
    before,
    beforeEach,
    createJobScopedGetter,
    expect,
    getCurrent,
    globals,
    registerDebugInfo,
} from "@odoo/hoot";
import { mockFetch, mockWebSocket } from "@odoo/hoot-mock";
import { assets } from "@web/core/assets";
import { RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { isIterable } from "@web/core/utils/arrays";
import { isObject } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { serverState } from "../mock_server_state.hoot";
import { fetchModelDefinitions, registerModelToFetch } from "../module_set.hoot";
import { DEFAULT_FIELD_VALUES, FIELD_SYMBOL } from "./mock_fields";
import {
    FIELD_NOT_FOUND,
    MockServerError,
    getRecordQualifier,
    makeKwArgs,
    makeServerError,
    safeSplit,
} from "./mock_server_utils";

const { fetch: realFetch } = globals;
const { DateTime } = luxon;

/**
 * @typedef {Record<string, any>} ActionDefinition
 *
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 *
 * @typedef {import("./mock_fields").FieldDefinition} FieldDefinition
 *
 * @typedef {{
 *  actionID?: string | number;
 *  appID?: number | "root";
 *  children?: MenuDefinition[];
 *  id: Number | "root";
 *  name: string;
 *  xmlId?: string;
 * }} MenuDefinition
 *
 * @typedef {MockServerBaseEnvironment & { [modelName: string]: Model }} MockServerEnvironment
 *
 * @typedef {import("./mock_model").Model} Model
 *
 * @typedef {import("./mock_model").ModelConstructor} ModelConstructor
 *
 * @typedef {(params: OrmParams) => any} OrmCallback
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
 * @typedef {{
 *  alwaysReturns?: boolean;
 *  pure?: boolean;
 * }} RouteOptions
 *
 * @typedef {{
 *  actions?: Partial<typeof MockServer["prototype"]["actions"]>;
 *  lang?: string;
 *  lang_parameters?: Partial<typeof MockServer["prototype"]["lang_parameters"]>;
 *  menus?: MenuDefinition[];
 *  models?: Iterable<ModelConstructor>;
 *  modules?: Partial<typeof MockServer["prototype"]["modules"]>;
 *  multi_lang?: import("../mock_server_state.hoot").ServerState["multiLang"];
 *  routes?: Parameters<MockServer["onRpc"]>;
 *  timezone?: string;
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
    env.uid = user.id;
};

/**
 * @template T
 * @param {T} object
 * @return {T}
 */
const deepCopy = (object) => {
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
};

/**
 * @param {unknown} error
 */
const ensureError = (error) => (error instanceof Error ? error : new Error(error));

const getCurrentMockServer = () => {
    const { test } = getCurrent();
    if (!test || !test.run) {
        return null;
    }
    if (!mockServers.has(test.run)) {
        mockServers.set(test.run, new MockServer());
    }
    return mockServers.get(test.run);
};

const getCurrentParams = createJobScopedGetter(
    /**
     * @param {ServerParams} previous
     */
    (previous) => ({
        ...previous,
        actions: deepCopy(previous?.actions || {}),
        embeddedActions: deepCopy(previous?.embeddedActions || []),
        menus: deepCopy(previous?.menus || [DEFAULT_MENU]),
        models: [...(previous?.models || [])], // own instance getters, no need to deep copy
        routes: [...(previous?.routes || [])], // functions, no need to deep copy
    })
);

/**
 * @param {unknown} value
 */
const isNil = (value) => value === null || value === undefined;

/**
 * @param {string} target
 * @param {string | RegExp} matcher
 */
const match = (target, matcher) => {
    if (matcher === "*") {
        return true;
    }
    if (matcher instanceof RegExp) {
        return matcher.test(target);
    } else {
        return target === matcher;
    }
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
        return MockServer.env["res.company"].read(serverState.companies.map((c) => c.id));
    }

    get company() {
        return this.companies[0];
    }

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

const DEFAULT_MENU = {
    id: 99999,
    appID: 1,
    children: [],
    name: "App0",
};
const R_DATASET_ROUTE = /\/web\/dataset\/call_(button|kw)\/[\w.-]+\/(?<step>\w+)/;
const R_WEBCLIENT_ROUTE = /(?<step>\/web\/webclient\/\w+)/;

const mockRpcRegistry = registry.category("mock_rpc");
/** @type {WeakMap<() => any, MockServer>} */
const mockServers = new WeakMap();
const serverFields = new WeakSet();

beforeEach((test) => {
    /**
     * @template T
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    const returnIfSameTest = async (promise) => {
        if (originalTestId) {
            const result = await promise;
            if (originalTestId === getCurrent().test?.id) {
                return result;
            }
        }
        return new Promise(() => {});
    };

    const originalTestId = test.id;

    return patch(assets, {
        async getBundle() {
            return returnIfSameTest(super.getBundle(...arguments));
        },
        async loadBundle() {
            return returnIfSameTest(super.loadBundle(...arguments));
        },
        async loadCSS() {
            return returnIfSameTest(super.loadCSS(...arguments));
        },
        async loadJS() {
            return returnIfSameTest(super.loadJS(...arguments));
        },
    });
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockServer {
    /** @type {MockServer | null} */
    static get current() {
        const mockServer = getCurrentMockServer();
        return mockServer?.started ? mockServer : null;
    }

    static get env() {
        return this.current?.env;
    }

    static get state() {
        return serverState;
    }

    // Server params
    lang_parameters = {
        date_format: "%m/%d/%Y",
        decimal_point: ".",
        direction: "ltr",
        grouping: [3, 0],
        time_format: "%H:%M:%S",
        short_time_format: "%H:%M",
        thousands_sep: ",",
        week_start: 7,
    };
    modules = {
        web: { messages: [] },
    };

    // Server env
    env = this.makeServerEnv();

    // Data
    /** @type {Record<string, ActionDefinition>} */
    actions = {};
    /** @type {Record<string, ActionDefinition>[]} */
    embeddedActions = [];
    /** @type {MenuDefinition[]} */
    menus = [];
    /** @type {Record<string, Model>} */
    models = {};
    /** @type {Record<string, ModelConstructor>} */
    modelSpecs = {};
    /** @type {Set<string>} */
    modelNamesToFetch = new Set();

    // Routes
    /** @type {[RegExp, string[], RouteCallback, RouteOptions][]} */
    routes = [];
    started = false;
    /** @type {[string, string, OrmCallback][]>} */
    ormListeners = [];

    // WebSocket connections
    /** @type {import("@odoo/hoot-mock").ServerWebSocket[]} */
    websockets = [];

    constructor() {
        // Set default routes
        this.onRpc("/web/action/load", this.mockActionLoad);
        this.onRpc("/web/action/load_breadcrumbs", this.mockActionLoadBreadcrumbs);
        this.onRpc("/web/bundle", this.mockBundle, { pure: true });
        this.onRpc("/web/dataset/call_kw", this.mockCallKw, { alwaysReturns: true });
        this.onRpc("/web/dataset/call_button", this.mockCallKw, { alwaysReturns: true });
        this.onRpc("/web/dataset/resequence", this.mockResequence);
        this.onRpc("/web/image/:model/:id/:field", this.mockImage, { pure: true });
        this.onRpc("/web/webclient/load_menus", this.mockLoadMenus, { pure: true });
        this.onRpc("/web/webclient/translations", this.mockLoadTranslations, { pure: true });

        mockFetch((input, init) => this.handle(input, init));
        mockWebSocket((ws) => this.websockets.push(ws));
    }

    /**
     * @param {OrmParams} params
     */
    callOrm(params) {
        const { method, model: modelName } = params;
        const args = params.args || [];
        const kwargs = makeKwArgs(params.kwargs || {});

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

        throw new MockServerError(`unimplemented ORM method: ${modelName}.${method}`);
    }

    /**
     * @param {Partial<ServerParams>} params
     */
    configure(params) {
        if (params.actions) {
            Object.assign(this.actions, params.actions);
        }
        if (params.embeddedActions) {
            this.embeddedActions.push(...params.embeddedActions);
        }
        if (params.lang) {
            serverState.lang = params.lang;
        }
        if (params.lang_parameters) {
            Object.assign(this.lang_parameters, params.lang_parameters);
        }
        if (params.menus) {
            this.menus.push(...params.menus);
        }
        if (params.models) {
            this.registerModels(params.models);
        }
        if (params.modules) {
            for (const [module, values] in Object.entries(params.modules)) {
                this.registerTranslations(module, values.message || values);
            }
        }
        if (params.multi_lang) {
            serverState.multiLang = params.multi_lang;
        }
        if (params.timezone) {
            serverState.timezone = params.timezone;
        }
        if (params.translations) {
            this.registerTranslations("web", params.translations);
        }
        if (params.routes) {
            for (const args of params.routes) {
                this.onRpc(...args);
            }
        }

        return this;
    }

    /**
     * @param {OrmParams} params
     */
    findOrmListeners({ method, model }) {
        const callbacks = [this.callOrm];
        for (const [listenerModel, listenerMethod, callback] of this.ormListeners) {
            if (match(model, listenerModel) && match(method, listenerMethod)) {
                callbacks.unshift(callback);
            }
        }
        return callbacks;
    }

    /**
     * @param {string} route
     */
    findRouteListeners(route) {
        /** @type {[RouteCallback, Record<string, string>, RouteOptions][]} */
        const listeners = [];
        for (const [regex, params, callback, options] of this.routes) {
            const match = route.match(regex);
            if (match) {
                const routeParams = {};
                for (let i = 0; i < params.length; i++) {
                    routeParams[params[i]] = match[i + 1];
                }
                listeners.unshift([callback, routeParams, options]);
            }
        }
        return listeners;
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
                    record[fieldName] ??= DEFAULT_FIELD_VALUES[fieldDef.type]?.() ?? false;
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
     * @param {string | number | false} id
     */
    getAction(id) {
        const action =
            this.actions[id] ||
            Object.values(this.actions).find((action) => {
                return action.xml_id === id || action.path === id;
            });
        if (!action) {
            throw makeServerError({
                errorName: "odoo.addons.web.controllers.action.MissingActionError",
                message: `The action ${JSON.stringify(id)} does not exist`,
            });
        }
        if (action.type === "ir.actions.act_window") {
            action["embedded_action_ids"] = this.embeddedActions.filter(
                (el) => el && el.parent_action_id === id
            );
        }
        return action;
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
        for (const [fieldName, fieldDescriptor] of Object.entries(ModelClass._fields)) {
            if (!(FIELD_SYMBOL in fieldDescriptor)) {
                continue;
            }

            if (fieldDescriptor.name) {
                throw new MockServerError(
                    `cannot set the name of field "${fieldName}" from its definition: got "${fieldDescriptor.name}"`
                );
            }
            fieldDescriptor.string ||= toDisplayName(fieldName);

            /** @type {FieldDefinition} */
            const fieldDef = { ...fieldDescriptor, name: fieldName };

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
     * @param {RouteOptions} [options]
     */
    async handle(url, init, options = {}) {
        if (!this.started) {
            throw new MockServerError(
                `cannot handle \`fetch\`: server has not been started (did you forget to call \`start()\`?)`
            );
        }

        const method = init?.method?.toUpperCase() || (init?.body ? "POST" : "GET");
        const request = new Request(url, { method, ...(init || {}) });

        const route = new URL(request.url).pathname;
        const listeners = this.findRouteListeners(route);
        if (!listeners.length) {
            throw new MockServerError(`unimplemented server route: ${route}`);
        }

        let result = null;
        for (const [callback, routeParams, routeOptions] of listeners) {
            try {
                result = await callback.call(this, request, routeParams);
            } catch (error) {
                result = ensureError(error);
            }
            if (!isNil(result) || (options.alwaysReturns ?? routeOptions.alwaysReturns)) {
                if (options.pure ?? routeOptions.pure) {
                    return result;
                }
                if (result instanceof RPCError) {
                    return { error: result, result: null };
                }
                if (result instanceof Error) {
                    return {
                        error: {
                            code: 418,
                            data: result,
                            message: result.message,
                            type: result.name,
                        },
                        result: null,
                    };
                }
                return { error: null, result };
            }
        }

        // There was a matching controller that wasn't call_kw but it didn't return anything: treat it as JSON
        return { error: null, result };
    }

    async loadModels() {
        const models = Object.values(this.modelSpecs);
        const serverModelInheritances = new Set();
        this.modelSpecs = {};
        if (this.modelNamesToFetch.size) {
            const modelEntries = await fetchModelDefinitions(this.modelNamesToFetch);
            this.modelNamesToFetch.clear();

            for (const [
                name,
                { description, fields, inherit, order, parent_name, rec_name, ...others },
            ] of modelEntries) {
                const localModelDef = models.find((model) => model._name === name);
                localModelDef._description = description;
                localModelDef._order = order;
                localModelDef._parent_name = parent_name;
                localModelDef._rec_name = rec_name;
                const inheritList = new Set(safeSplit(localModelDef._inherit));
                for (const inherittedModelName of inherit) {
                    inheritList.add(inherittedModelName);
                    serverModelInheritances.add([name, inherittedModelName].join(","));
                }
                localModelDef._inherit = [...inheritList].join(",");
                for (const name in others) {
                    localModelDef[name] = others[name];
                }
                for (const [fieldName, serverFieldDef] of Object.entries(fields)) {
                    const serverField = {
                        ...serverFieldDef,
                        ...localModelDef._fields[fieldName],
                    };
                    serverFields.add(serverField);
                    localModelDef._fields[fieldName] = serverField;
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

            if (model._name in this.env) {
                throw new MockServerError(
                    `cannot register model "${model._name}": a model or a server environment property with the same name already exists`
                );
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

            // Check missing models
            for (const field of Object.values(model._fields)) {
                if (field.relation && !this.models[field.relation]) {
                    if (serverFields.has(field)) {
                        delete model._fields[field.name];
                    } else {
                        throw modelNotFoundError(field.relation, "could not find model");
                    }
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
        const serverEnv = new MockServerBaseEnvironment();
        return new Proxy(serverEnv, {
            get: (target, p) => {
                if (p in target || typeof p !== "string" || p === "then") {
                    return Reflect.get(target, p);
                }
                const model = Reflect.get(this.models, p);
                if (!model) {
                    throw modelNotFoundError(p, "could not get model from server environment");
                }
                return model;
            },
            has: (target, p) => Reflect.has(target, p) || Reflect.has(this.models, p),
        });
    }

    /**
     * @overload
     * @param {OrmCallback} callback
     */
    /**
     * @overload
     * @param {string} method
     * @param {OrmCallback} callback
     */
    /**
     * @overload
     * @param {string} model
     * @param {string} method
     * @param {OrmCallback} callback
     */
    /**
     * @param {string | OrmCallback} model
     * @param {string | OrmCallback} [method]
     * @param {OrmCallback} [callback]
     */
    onOrmMethod(...args) {
        const callback = args.pop();
        const method = args.pop() || "*";
        const model = args.pop() || "*";
        this.ormListeners.push([model, method, callback]);
    }

    /**
     * @param {`/${string}`} route
     * @param {RouteCallback} callback
     * @param {RouteOptions} options
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
        this.routes.push([routeRegex, routeParams, callback, options || {}]);
    }

    /**
     * @overload
     * @param {OrmCallback} callback
     */
    /**
     * @overload
     * @param {`/${string}`} route
     * @param {RouteCallback} callback
     * @param {RouteOptions} [options]
     */
    /**
     * @overload
     * @param {string | RegExp} method
     * @param {OrmCallback} callback
     */
    /**
     * @overload
     * @param {string} model
     * @param {string | RegExp} method
     * @param {OrmCallback} callback
     */
    /**
     * @param {string | OrmCallback | RegExp} route
     * @param {RouteCallback | OrmCallback | string | RegExp} [callback]
     * @param {RouteOptions | OrmCallback} [options]
     */
    onRpc(...args) {
        if (typeof args[0] === "string" && args[0].startsWith("/")) {
            this.onRoute(...args);
        } else {
            this.onOrmMethod(...args);
        }
        return this;
    }

    /**
     * @param {Iterable<ModelConstructor>} ModelClasses
     */
    registerModels(ModelClasses) {
        for (const ModelClass of ModelClasses) {
            const model = this.getModelDefinition(ModelClass);
            this.modelSpecs[model._name] = model;
        }

        if (this.started) {
            this.loadModels();
        }
    }

    /**
     * @param {string} module
     * @param {Record<string, string>} translations
     */
    registerTranslations(module, translations) {
        this.modules[module] ||= {};
        this.modules[module].messages ||= {};
        if (Array.isArray(translations)) {
            this.modules.web.messages.push(...translations);
        } else {
            for (const [id, string] of Object.entries(translations)) {
                this.modules.web.messages.push({ id, string });
            }
        }
    }

    async start() {
        if (this.started) {
            throw new MockServerError("MockServer has already been started");
        }
        this.started = true;

        await this.loadModels();
        this.generateRecords();

        return this;
    }

    //-------------------------------------------------------------------------
    // Route methods
    //-------------------------------------------------------------------------

    /** @type {RouteCallback} */
    async mockActionLoad(request) {
        const { params } = await request.json();
        return this.getAction(params.action_id);
    }

    /** @type {RouteCallback} */
    async mockActionLoadBreadcrumbs(request) {
        const { params } = await request.json();
        const { actions } = params;
        return actions.map(({ action: actionId, model, resId }) => {
            if (actionId) {
                const action = this.getAction(actionId);
                if (resId) {
                    return {
                        display_name: this.env[action.res_model].read([resId], ["display_name"])[0]
                            .display_name,
                    };
                }
                return { display_name: action.name };
            } else if (model) {
                if (resId) {
                    return {
                        display_name: this.env[model].read([resId], ["display_name"])[0]
                            .display_name,
                    };
                }
                throw new Error("Actions with a model should also have a resId");
            }
            throw new Error("Actions should have either an action (id or path) or a model");
        });
    }

    /** @type {RouteCallback} */
    async mockBundle(request) {
        // No mock here: we want to fetch the actual bundle
        return realFetch(request.url);
    }

    /** @type {RouteCallback} */
    async mockCallKw(request) {
        const callNextOrmCallback = () => {
            const nextCallback = ormListeners.shift();
            return nextCallback.call(this, callbackParams);
        };

        const { params } = await request.json();
        const callbackParams = {
            parent: callNextOrmCallback,
            request,
            route: new URL(request.url).pathname,
            ...params,
        };
        const ormListeners = this.findOrmListeners(params);
        while (ormListeners.length) {
            const result = await callNextOrmCallback();
            if (!isNil(result)) {
                return result;
            }
        }
        return null;
    }

    /** @type {RouteCallback} */
    async mockImage(request, { model, field, id }) {
        return `<fake url to record ${id} on ${model}.${field}>`;
    }

    /** @type {RouteCallback} */
    async mockLoadMenus() {
        const root = { id: "root", children: [], name: "root", appID: "root" };
        const menuDict = { root };

        const recursive = [{ isRoot: true, menus: this.menus }];
        for (const { isRoot, menus } of recursive) {
            for (const _menu of menus) {
                if (isRoot) {
                    root.children.push(_menu.id);
                }
                const menu = { ..._menu };
                const children = menu.children || [];
                menu.children = children.map((m) => m.id);
                recursive.push({ isRoot: false, menus: children });
                menuDict[menu.id] = menu;
            }
        }
        return menuDict;
    }

    /** @type {RouteCallback} */
    async mockLoadTranslations() {
        const langParameters = { ...this.lang_parameters };
        if (typeof langParameters.grouping !== "string") {
            langParameters.grouping = JSON.stringify(langParameters.grouping);
        }
        return {
            lang: serverState.lang,
            lang_parameters: langParameters,
            modules: this.modules,
            multi_lang: serverState.multiLang,
        };
    }

    /** @type {RouteCallback} */
    async mockResequence(request) {
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
 */
export function defineActions(actions) {
    return defineParams(
        { actions: Object.fromEntries(actions.map((a) => [a.id || a.xml_id, { ...a }])) },
        "add"
    ).actions;
}

/**
 * @param {ActionDefinition[]} actions
 */
export function defineEmbeddedActions(actions) {
    return defineParams(
        { embeddedActions: Object.fromEntries(actions.map((a) => [a.id || a.xml_id, { ...a }])) },
        "add"
    ).embeddedActions;
}

/**
 * @param {MenuDefinition[]} menus
 */
export function defineMenus(menus) {
    return defineParams({ menus }, "add").menus;
}

/**
 * Registers a list of model classes on the current/future {@link MockServer} instance.
 *
 * @param  {ModelConstructor[] | Record<string, ModelConstructor>} ModelClasses
 */
export function defineModels(ModelClasses) {
    const models = Object.values(ModelClasses);
    for (const ModelClass of models) {
        const instance = new ModelClass();
        // we cannot get the `definition` as this will trigger the model creation
        if (instance._fetch) {
            registerModelToFetch(instance._name);
        }
    }

    return defineParams({ models }, "add").models;
}

/**
 * @param {ServerParams} params
 * @param {"add" | "replace"} [mode="replace"]
 */
export function defineParams(params, mode) {
    before(() => {
        const currentParams = getCurrentParams();
        for (const [key, value] of Object.entries(params)) {
            if (mode === "add" && isObject(value)) {
                if (isIterable(value)) {
                    currentParams[key] ||= [];
                    currentParams[key].push(...value);
                } else {
                    currentParams[key] ||= {};
                    Object.assign(currentParams[key], value);
                }
            } else {
                currentParams[key] = value;
            }
        }

        MockServer.current?.configure(params);
    });

    return params;
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
 */
export async function makeMockServer() {
    const mockServer = getCurrentMockServer();

    // Add routes from "mock_rpc" registry
    for (const [route, callback] of mockRpcRegistry.getEntries()) {
        if (typeof callback === "function") {
            mockServer.onRpc(route, callback);
        }
    }

    // Add other ambiant params
    mockServer.configure(getCurrentParams());

    registerDebugInfo(mockServer);

    return mockServer.start();
}

/**
 * @overload
 * @param {OrmCallback} callback
 */
/**
 * @overload
 * @param {`/${string}`} route
 * @param {RouteCallback} callback
 * @param {RouteOptions} [options]
 */
/**
 * @overload
 * @param {string | RegExp} method
 * @param {OrmCallback} callback
 */
/**
 * @overload
 * @param {string} model
 * @param {string | RegExp} method
 * @param {OrmCallback} callback
 */
/**
 * Registers an RPC handler on the current/future {@link MockServer} instance.
 *
 * @type {MockServer["onRpc"]}
 */
export function onRpc(...args) {
    return defineParams({ routes: [args] }, "add").routes;
}

/**
 * calls expect.step for all network calls. Because of how the mock server
 * works, you need to call this *after* all your custom mockRPCs that return
 * something, otherwise the mock server will not call this function's handler.
 *
 * @returns {void}
 */
export function stepAllNetworkCalls() {
    onRpc("/", (request) => {
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
