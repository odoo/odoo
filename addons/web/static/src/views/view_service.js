/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * @typedef {Object} Fields
 */

/**
 * @typedef {string} ViewType // to define
 */

/**
 * @typedef {Object} Toolbar // to precise
 * @property {?} print
 * @property {?} action
 */

/**
 * @typedef {Object} IrFilter
 * @property {[number, string] | false} user_id
 * @property {string} sort
 * @property {string} context
 * @property {string} name
 * @property {string} domain
 * @property {number} id
 * @property {boolean} is_default
 * @property {string} model_id
 * @property {[number, string] | false} action_id
 */

/**
 * @typedef {Object} ViewDescription
 * @property {string} arch
 * @property {Fields} [fields]
 * @property {string} model
 * @property {string} [name] is returned by the server ("default" or real name)
 * @property {ViewType} type
 * @property {number} [viewId]
 * @property {Object} [toolbar] // for views other than search
 * @property {IrFilter[]} [irFilters] // for search view
 */

/**
 * @typedef {Object} LoadViewsParams
 * @property {string} resModel
 * @property {[number, ViewType][]} views
 * @property {Object} context
 */

/**
 * @typedef {Object} LoadViewsOptions
 * @property {number} actionId
 * @property {boolean} loadActionMenus
 * @property {boolean} loadIrFilters
 */

export const viewService = {
    name: "view",
    dependencies: ["orm"],
    start(env, { orm }) {
        let cache = {};

        env.bus.on("CLEAR-CACHES", null, () => {
            cache = {};
        });

        /**
         * Loads various information concerning views: fields_view for each view,
         * fields of the corresponding model, and optionally the filters.
         *
         * @param {LoadViewsParams} params
         * @param {LoadViewsOptions} options
         * @returns {Promise<ViewDescriptions>}
         */
        async function loadViews(params, options) {
            const key = JSON.stringify([params.resModel, params.views, params.context, options]);
            if (!cache[key]) {
                cache[key] = orm
                    .call(params.resModel, "load_views", [], {
                        views: params.views,
                        options: {
                            action_id: options.actionId || false,
                            load_filters: options.loadIrFilters || false,
                            toolbar: options.loadActionMenus || false,
                        },
                        context: params.context,
                    })
                    .then((result) => {
                        const viewDescriptions = {
                            __legacy__: result,
                        }; // for legacy purpose, keys in result are left in viewDescriptions
                        for (const [_, viewType] of params.views) {
                            const viewDescription = JSON.parse(
                                JSON.stringify(result.fields_views[viewType])
                            );
                            viewDescription.viewId = viewDescription.view_id;
                            delete viewDescription.view_id;
                            if (viewDescription.toolbar) {
                                viewDescription.actionMenus = viewDescription.toolbar;
                                delete viewDescription.toolbar;
                            }
                            viewDescription.fields = Object.assign(
                                {},
                                result.fields,
                                viewDescription.fields
                            ); // before a deep freeze was done.
                            delete viewDescription.base_model; // unused
                            delete viewDescription.field_parent; // unused
                            if (viewType === "search" && options.loadIrFilters) {
                                viewDescription.irFilters = result.filters;
                            }
                            viewDescriptions[viewType] = viewDescription;
                        }
                        return viewDescriptions;
                    })
                    .catch((error) => {
                        delete cache[key];
                        return Promise.reject(error);
                    });
            }
            return cache[key];
        }
        return { loadViews };
    },
};

registry.category("services").add("view", viewService);
