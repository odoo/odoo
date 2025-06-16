import { RPCError } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { Deferred, Race } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { SEARCH_KEYS } from "@web/search/with_search/with_search";
import { buildSampleORM } from "./sample_server";

import {
    EventBus,
    onMounted,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    status,
    useComponent,
} from "@odoo/owl";

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 */

export class Model {
    /**
     * @param {Object} env
     * @param {Object} services
     */
    constructor(env, params, services) {
        this.env = env;
        this.orm = services.orm;
        this.bus = new EventBus();
        this.isReady = false;
        this.whenReady = new Deferred();
        this.whenReady.then(() => {
            this.isReady = true;
            this.notify();
        });
        this.setup(params, services);
    }

    /**
     * @param {Object} params
     * @param {Object} services
     */
    setup(/* params, services */) {}

    /**
     * @param {SearchParams} searchParams
     */
    async load(/* searchParams */) {}

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
Model.services = [];

/**
 * @param {Object} props
 * @returns {SearchParams}
 */
function getSearchParams(props) {
    const params = {};
    for (const key of SEARCH_KEYS) {
        params[key] = props[key];
    }
    return params;
}

function usePostMountedServices(services) {
    if (services.dialog) {
        services.dialog = Object.create(services.dialog);
        const dialogAddOrigin = services.dialog.add;
        let dialogRequests = [];
        services.dialog.add = (...args) => {
            const index = dialogRequests.push(args);
            return () => {
                dialogRequests[index] = null;
            };
        };
        onMounted(() => {
            services.dialog.add = dialogAddOrigin;
            for (const req of dialogRequests) {
                if (req) {
                    dialogAddOrigin(...req);
                }
            }
            dialogRequests = null;
        });
    }
    return services;
}

/**
 * @template {typeof Model} T
 * @param {T} ModelClass
 * @param {Object} params
 * @param {Object} [options]
 * @param {Function} [options.beforeFirstLoad]
 * @returns {InstanceType<T>}
 */
export function useModel(ModelClass, params, options = {}) {
    const component = useComponent();
    let services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    services.orm = services.orm || useService("orm");
    services = usePostMountedServices(services);
    const model = new ModelClass(component.env, params, services);
    onWillStart(async () => {
        await options.beforeFirstLoad?.();
        await model.load(component.props);
        model.whenReady.resolve();
    });
    onWillUpdateProps((nextProps) => model.load(nextProps));
    return model;
}

/**
 * @template {typeof Model} T
 * @param {T} ModelClass
 * @param {Object} params
 * @param {Object} [options]
 * @param {Function} [options.lazy=false]
 * @returns {InstanceType<T>}
 */
export function useModelWithSampleData(ModelClass, params, options = {}) {
    const component = useComponent();
    if (!(ModelClass.prototype instanceof Model)) {
        throw new Error(`the model class should extend Model`);
    }
    let services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    services.orm = services.orm || useService("orm");
    services = usePostMountedServices(services);

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

    async function _load(props) {
        const searchParams = getSearchParams(props);
        await model.load(searchParams);
        if (useSampleModel && !model.hasData()) {
            sampleORM =
                sampleORM || buildSampleORM(component.props.resModel, component.props.fields, user);
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
