/** @odoo-module **/

import { SEARCH_KEYS } from "@web/search/with_search/with_search";
import { useBus } from "@web/core/bus_hook";
import { useService } from "@web/core/service_hook";

const { core, hooks } = owl;
const { EventBus } = core;
const { useComponent, onWillStart, onWillUpdateProps } = hooks;

export class Model extends EventBus {
    /**
     * @param {Object} env
     * @param {Object} services
     */
    constructor(env, services) {
        super();
        this.env = env;
        this.setup(services);
    }

    /**
     * @param {Object} services
     */
    setup(services) {}

    /**
     * @param {Object} params
     */
    load(params) {}

    /**
     * @param {Object} params
     */
    reload(params) {}

    notify() {
        this.trigger("update");
    }
}
Model.services = [];

/**
 * @template {Model} T
 * @param {new (env: Object, services: Object) => T} ModelClass
 * @param {Object} loadParams
 * @param {Object} [options]
 * @param {Function} [options.onUpdate]
 * @returns {T}
 */
export function useModel(ModelClass, loadParams, options = {}) {
    const component = useComponent();
    if (!(ModelClass.prototype instanceof Model)) {
        throw new Error(`the model class should extend Model`);
    }
    const services = {};
    for (const key of ModelClass.services) {
        services[key] = useService(key);
    }
    const model = new ModelClass(component.env, services);
    useBus(model, "update", options.onUpdate || component.render);

    const initialGroupBy = (loadParams.groupBy || component.props.groupBy).slice();

    onWillStart(() => {
        return model.load(loadParams);
    });

    onWillUpdateProps((nextProps) => {
        const params = {};
        for (const key of SEARCH_KEYS) {
            params[key] = nextProps[key];
        }
        if (params.groupBy && params.groupBy.length === 0) {
            params.groupBy = initialGroupBy;
        }
        params.useSampleModel = false;
        return model.reload(params);
    });
    return model;
}
