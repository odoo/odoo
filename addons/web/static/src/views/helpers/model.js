/** @odoo-module **/

import { SEARCH_KEYS } from "@web/search/with_search/with_search";
import { useBus, useService } from "@web/core/utils/hooks";
import { buildSampleORM } from "@web/views/helpers/sample_server";
import { useSetupView } from "@web/views/helpers/view_hook";

const { core, hooks } = owl;
const { EventBus } = core;
const { onWillStart, onWillUpdateProps, useComponent } = hooks;

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
    useBus(model, "update", options.onUpdate || component.render);

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
    async function load(props) {
        model.orm = orm;
        const searchParams = getSearchParams(props);
        await model.load(searchParams);
        if (useSampleModel && !model.hasData()) {
            sampleORM =
                sampleORM || buildSampleORM(component.props.resModel, component.props.fields, user);
            model.orm = sampleORM;
            await model.load(searchParams);
        } else {
            useSampleModel = false;
        }
        model.useSampleModel = useSampleModel;
    }
    onWillStart(() => {
        return load(component.props);
    });
    onWillUpdateProps((nextProps) => {
        useSampleModel = false;
        return load(nextProps);
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
