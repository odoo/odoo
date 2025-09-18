// @ts-check

/** @module @web/model/model - Abstract base Model class with OWL lifecycle integration and sample data fallback */

import {
    EventBus,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    status,
    useComponent,
} from "@odoo/owl";
import { useSetupAction } from "@web/core/action_hook";
import { SEARCH_KEYS } from "@web/core/constants";
import { RPCError } from "@web/core/network/rpc";
import { Deferred, Race } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/services/user";

import { buildSampleORM } from "./sample_server";

/** @import { OdooEnv } from "@web/env" */
/** @import { SearchParams } from "@web/search/search_model" */
/** @import { ServiceFactories as Services } from "services" */

export class Model {
    static services = [];

    /**
     * @param {OdooEnv} env
     * @param {Object} params
     * @param {Object} services
     */
    constructor(env, params, services) {
        this.env = env;
        this.orm = services.orm;
        this.bus = new EventBus();
        this.isReady = false;
        /** @type {boolean} */
        this.useSampleModel = false;
        /**
         * The root data point, set by subclass `load()` implementations
         * (e.g. a Record, DynamicRecordList, or DynamicGroupList).
         * @type {any}
         */
        this.root = undefined;
        /**
         * Model metadata, set by subclass implementations
         * (e.g. GraphModel, PivotModel).
         * @type {any}
         */
        this.metaData = undefined;
        /**
         * Model data, set by subclass implementations
         * (e.g. PivotModel, GraphModel).
         * @type {any}
         */
        this.data = undefined;
        /**
         * Model configuration, set by subclass implementations
         * (e.g. RelationalModel).
         * @type {any}
         */
        this.config = undefined;
        /** @type {Deferred} */
        this.whenReady = new Deferred();
        this.whenReady.then(() => {
            this.isReady = true;
            this.notify();
        });
        this.setup(params, services);
    }

    /**
     * @param {Object} _params
     * @param {Object} _services
     */
    setup(_params, _services) {}

    /**
     * @param {Partial<SearchParams>} [_params]
     */
    async load(_params) {}

    /**
     * This function is meant to be overriden by models that want to implement
     * the sample data feature. It should return true iff the last loaded state
     * actually contains data. If not, another load will be done (if the sample
     * feature is enabled) with the orm service substituted by another using the
     * SampleServer, to have sample data to display instead of an empty screen.
     *
     * @returns {boolean}
     */
    hasData() {
        return true;
    }

    /**
     * This function is meant to be overriden by models that want to combine
     * sample data with real groups that exist on the server.
     *
     * @returns {boolean}
     */
    getGroups() {
        return null;
    }

    notify() {
        this.bus.trigger("update");
    }
}

/**
 * @param {Record<string, unknown>} props
 * @returns {Object}
 */
function getSearchParams(props) {
    const params = {};
    for (const key of SEARCH_KEYS) {
        params[key] = props[key];
    }
    return params;
}

/**
 * @param {typeof Model} ModelClass
 * @param {Object} params
 * @param {Object} [options]
 * @param {Function} [options.beforeFirstLoad]
 * @returns {Model}
 */
export function useModel(ModelClass, params, options = {}) {
    const component = useComponent();
    /** @type {Record<string, any>} */
    const services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    services.orm = services.orm || useService("orm");
    const model = new ModelClass(component.env, params, services);
    onWillStart(async () => {
        await options.beforeFirstLoad?.();
        await model.load(getSearchParams(component.props));
        model.whenReady.resolve();
    });
    onWillUpdateProps((nextProps) => model.load(getSearchParams(nextProps)));
    return model;
}

/**
 * @param {typeof Model} ModelClass
 * @param {Object} params
 * @param {Object} [options]
 * @param {Function} [options.lazy=false]
 * @returns {Model}
 */
export function useModelWithSampleData(ModelClass, params, options = {}) {
    const component = useComponent();
    if (!(ModelClass.prototype instanceof Model)) {
        throw new Error(`the model class should extend Model`);
    }
    /** @type {Record<string, any>} */
    const services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    services.orm = services.orm || useService("orm");

    if (!("isAlive" in params)) {
        params.isAlive = () => status(component) !== "destroyed";
    }

    const model = new ModelClass(component.env, params, services);

    const onUpdate = () => component.render(true);
    model.bus.addEventListener("update", onUpdate);
    onWillUnmount(() => model.bus.removeEventListener("update", onUpdate));

    const globalState = component.props.globalState || {};
    const localState = component.props.state || {};
    let useSampleModel =
        component.props.useSampleModel &&
        (!("useSampleModel" in globalState) || globalState.useSampleModel);
    model.useSampleModel = false;
    const orm = model.orm;
    let sampleORM = localState.sampleORM;

    /**
     * @param {Record<string, unknown>} props
     */
    async function _load(props) {
        const searchParams = getSearchParams(props);
        await model.load(searchParams);
        if (useSampleModel && !model.hasData()) {
            sampleORM =
                sampleORM ||
                buildSampleORM(component.props.resModel, component.props.fields, user);
            // Load data with sampleORM then restore real ORM.
            model.orm = sampleORM;
            await model.load(searchParams);
            model.orm = orm;
            model.useSampleModel = true;
        } else {
            useSampleModel = false;
            model.useSampleModel = useSampleModel;
        }
        model.whenReady.resolve(); // resolve after the first successful load
        if (status(component) === "mounted") {
            model.notify();
        }
    }
    const race = new Race();
    const load = (props) => race.add(_load(props));
    onWillStart(() => {
        const prom = load(component.props);
        if (options.lazy) {
            // in-house error handling as we're out of willStart
            prom.catch((e) => {
                if (e instanceof RPCError) {
                    component.env.config.historyBack();
                }
                throw e;
            });
        } else {
            return prom;
        }
    });
    onWillUpdateProps((nextProps) => {
        useSampleModel = false;
        load(nextProps);
    });

    useSetupAction({
        getGlobalState() {
            if (component.props.useSampleModel) {
                return { useSampleModel };
            }
        },
        getLocalState: () => ({ sampleORM }),
    });

    return model;
}

function _makeFieldFromPropertyDefinition(name, definition, relatedPropertyField) {
    return {
        ...definition,
        name,
        propertyName: definition.name,
        relation: definition.comodel,
        relatedPropertyField,
    };
}

export async function addPropertyFieldDefs(orm, resModel, context, fields, groupBy) {
    const proms = [];
    for (const gb of groupBy) {
        if (gb in fields) {
            continue;
        }
        const [fieldName] = gb.split(".");
        const field = fields[fieldName];
        if (field?.type === "properties") {
            proms.push(
                orm
                    .call(resModel, "get_property_definition", [gb], {
                        context,
                    })
                    .then((definition) => {
                        fields[gb] = _makeFieldFromPropertyDefinition(
                            gb,
                            definition,
                            field,
                        );
                    })
                    .catch(() => {
                        fields[gb] = _makeFieldFromPropertyDefinition(gb, {}, field);
                    }),
            );
        }
    }
    return Promise.all(proms);
}
