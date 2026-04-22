import { RPCError } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { Race } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { render, useComponent } from "@web/owl2/utils";
import { useSetupAction } from "@web/search/action_hook";
import { SEARCH_KEYS } from "@web/search/with_search/with_search";
import { buildSampleORM } from "./sample_server";

import { EventBus, onWillStart, onWillUnmount, onWillUpdateProps, signal, status } from "@odoo/owl";

/**
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 * @typedef {import("services").ServiceFactories} Services
 *
 * @typedef {{
 *  beforeFirstLoad?: () => any;
 *  lazy?: boolean;
 *  onLoad?: (searchParams: SearchParams) => any;
 * }} UseModelOptions
 */

export class Model {
    static services = [];

    /**
     * @param {OdooEnv} env
     * @param {SearchParams} params
     * @param {Services} services
     */
    constructor(env, params, services) {
        this.env = env;
        this.orm = services.orm;
        this.bus = new EventBus();
        this.isReady = signal(false);
        this.whenReady = Promise.withResolvers();
        this.whenReady.promise.then(() => {
            this.isReady.set(true);
            // this.notify();
        });
        this.setup(params, services);
    }

    /**
     * @param {SearchParams} params
     * @param {Services} services
     */
    setup(/* params, services */) {}

    /**
     * @param {Partial<SearchParams>} _params
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
 * @returns {SearchParams}
 */
function getSearchParams(props) {
    const params = {};
    for (const key of SEARCH_KEYS) {
        params[key] = props[key];
    }
    return params;
}

/**
 * @template {typeof Model} T
 * @param {T} ModelClass
 * @param {SearchParams} params
 * @param {UseModelOptions} [options]
 * @returns {InstanceType<T>}
 */
function _useModel(ModelClass, params, options) {
    if (!(ModelClass.prototype instanceof Model)) {
        throw new Error(`the model class should extend Model`);
    }

    /**
     * @param {Record<any, any>} props
     */
    async function load(props) {
        const searchParams = getSearchParams(props);
        await model.load(searchParams);

        if (onLoad) {
            await onLoad(searchParams);
        }

        if (!model.isReady()) {
            model.whenReady.resolve(); // resolve after the first successful load
        } else if (status(component) === "mounted") {
            model.notify();
        }
    }

    function onUpdate() {
        return render(component, true);
    }

    /**
     * @param {Record<any, any>} props
     */
    function raceLoad(props) {
        return race.add(load(props));
    }

    const race = new Race();
    const component = useComponent();
    const services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    services.orm ||= useService("orm");

    params.isAlive ??= function isAlive() {
        return status(component) !== "destroyed";
    };

    const { beforeFirstLoad, onLoad, lazy } = options || {};
    const env = component.env;
    const model = new ModelClass(env, params, services);

    model.bus.addEventListener("update", onUpdate);
    onWillUnmount(() => model.bus.removeEventListener("update", onUpdate));

    onWillStart(async () => {
        if (beforeFirstLoad) {
            await options.beforeFirstLoad();
        }
        const promise = raceLoad(component.props);
        if (lazy) {
            // in-house error handling as we're out of willStart
            promise.catch((e) => {
                if (e instanceof RPCError) {
                    env.config.historyBack();
                }
                throw e;
            });
        } else {
            await promise;
        }
    });
    onWillUpdateProps(raceLoad);

    return model;
}

/**
 * @template {typeof Model} T
 * @param {T} ModelClass
 * @param {SearchParams} params
 * @param {UseModelOptions} [options]
 * @returns {InstanceType<T>}
 */
export function useModel(ModelClass, params, options) {
    return _useModel(ModelClass, params, options);
}

/**
 * @template {typeof Model} T
 * @param {T} ModelClass
 * @param {SearchParams} params
 * @param {UseModelOptions} [options]
 * @returns {InstanceType<T>}
 */
export function useModelWithSampleData(ModelClass, params, options) {
    const component = useComponent();

    const globalState = component.props.globalState || {};
    const localState = component.props.state || {};

    let useSampleModel =
        component.props.useSampleModel &&
        (!("useSampleModel" in globalState) || globalState.useSampleModel);

    onWillUpdateProps(() => {
        useSampleModel = false;
    });

    const model = _useModel(ModelClass, params, {
        ...options,
        async onLoad(searchParams) {
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
        },
    });
    const orm = model.orm;

    model.useSampleModel = false;
    let sampleORM = localState.sampleORM;

    // Always disable the sample model when `load` is called (can be called by the view itself).
    // Note: the only case where the sample mode should be kept after a load is handled below (see
    // @load), and in that case, the flag is directly set to true afterwards.
    if (useSampleModel) {
        const originalLoad = model.load;
        model.load = async function () {
            const result = await originalLoad.call(this, ...arguments);
            this.useSampleModel = false;
            return result;
        };
    }

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

export function _makeFieldFromPropertyDefinition(name, definition, relatedPropertyField) {
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
                        fields[gb] = _makeFieldFromPropertyDefinition(gb, definition, field);
                    })
                    .catch(() => {
                        fields[gb] = _makeFieldFromPropertyDefinition(gb, {}, field);
                    })
            );
        }
    }
    return Promise.all(proms);
}
