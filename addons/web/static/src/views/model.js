/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { SEARCH_KEYS } from "@web/search/with_search/with_search";
import { buildSampleORM } from "@web/views/sample_server";
import { useSetupView } from "@web/views/view_hook";

const { EventBus, onWillStart, onWillUpdateProps, useComponent } = owl;

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 */

export class Model extends EventBus {
    /**
     * @param {Object} env
     * @param {Object} services
     */
    constructor(env, params, services) {
        super();
        this.env = env;
        this.orm = services.orm;
        this.useSampleModel = false; // will be set to true by the "useModel" hook if necessary
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
        this.trigger("update");
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

/**
 * @template {Model} T
 * @param {new (env: Object, params: Object, services: Object) => T} ModelClass
 * @param {Object} params
 * @param {Object} [options]
 * @param {Function} [options.onUpdate]
 * @returns {T}
 */
export function useModel(ModelClass, params, options = {}) {
    const component = useComponent();
    if (!(ModelClass.prototype instanceof Model)) {
        throw new Error(`the model class should extend Model`);
    }
    const services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    services.orm = services.orm || useService("orm");

    const model = new ModelClass(component.env, params, services);
    useBus(
        model,
        "update",
        options.onUpdate ||
            (() => {
                component.render(true); // FIXME WOWL reactivity
            })
    );

    const globalState = component.props.globalState || {};
    let useSampleModel = Boolean(
        "useSampleModel" in globalState
            ? globalState.useSampleModel
            : component.props.useSampleModel
    );
    model.useSampleModel = useSampleModel;
    const orm = model.orm;
    let sampleORM = globalState.sampleORM;
    const user = useService("user");
    let started = false;
    async function load(props) {
        const searchParams = getSearchParams(props);
        await model.load(searchParams);
        if (!options.ignoreUseSampleModel) {
            if (useSampleModel && !model.hasData()) {
                sampleORM =
                    sampleORM ||
                    buildSampleORM(component.props.resModel, component.props.fields, user);
                sampleORM.setGroups(model.getGroups());
                // Load data with sampleORM then restore real ORM.
                model.orm = sampleORM;
                await model.load(searchParams);
                model.orm = orm;
            } else {
                useSampleModel = false;
                model.useSampleModel = useSampleModel;
            }
        }
        if (started) {
            model.notify();
        }
    }
    onWillStart(async () => {
        // FIXME: we have a problem here: in the view, we have two onWillStart:
        //  - 1) to load the subviews that aren't inline
        //  - 2) to load the data
        //  2) must be done after 1), but we can't sync two onWillStarts
        // The problem is also there with the relational model, but it isn't visible
        // in the tests because the load the sub views in a tick, and we look inside
        // the fieldsInfo after a tick as well. Here, we look into fieldsInfo directly.
        if (params.beforeLoadProm) {
            await params.beforeLoadProm;
        }
        await load(component.props);
        started = true;
    });
    onWillUpdateProps((nextProps) => {
        useSampleModel = false;
        load(nextProps);
    });

    useSetupView({
        getGlobalState() {
            return {
                sampleORM,
                useSampleModel: model.useSampleModel,
            };
        },
    });

    return model;
}
