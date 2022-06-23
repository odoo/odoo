/** @odoo-module **/

import { deepCopy } from "@web/core/utils/objects";
import { registry } from "@web/core/registry";
import { generateLegacyLoadViewsResult } from "@web/legacy/legacy_load_views";

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
 * @property {Object} fields
 * @property {string} model
 * @property {string} [name] is returned by the server ("default" or real name)
 * @property {string} type
 * @property {number} [viewId]
 * @property {Object} [actionMenus] // for views other than search
 * @property {IrFilter[]} [irFilters] // for search view
 */

/**
 * @typedef {Object} LoadViewsParams
 * @property {string} resModel
 * @property {[number, string][]} views
 * @property {Object} context
 */

/**
 * @typedef {Object} LoadViewsOptions
 * @property {number|false} actionId
 * @property {boolean} loadActionMenus
 * @property {boolean} loadIrFilters
 */

export const viewService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let cache = {};

        env.bus.addEventListener("CLEAR-CACHES", () => {
            cache = {};
            const processedArchs = registry.category("__processed_archs__");
            processedArchs.content = {};
            processedArchs.trigger("UPDATE");
        });

        /**
         * Loads various information concerning views: fields_view for each view,
         * fields of the corresponding model, and optionally the filters.
         *
         * @param {LoadViewsParams} params
         * @param {LoadViewsOptions} [options={}]
         * @returns {Promise<ViewDescriptions>}
         */
        async function loadViews(params, options = {}) {
            const loadViewsOptions = {
                action_id: options.actionId || false,
                load_filters: options.loadIrFilters || false,
                toolbar: options.loadActionMenus || false,
            };
            if (env.isSmall) {
                loadViewsOptions.mobile = true;
            }
            const { context, resModel, views } = params;
            let filteredContext = Object.fromEntries(
                Object.entries(context || {}).filter((k, v) => !String(k).startsWith("default_"))
            );
            const key = JSON.stringify([resModel, views, filteredContext, loadViewsOptions]);
            if (!cache[key]) {
                cache[key] = orm
                    .call(resModel, "get_views", [], { context, views, options: loadViewsOptions })
                    .then((result) => {
                        const { models, views } = result;
                        const modelsCopy = deepCopy(models); // for legacy views
                        const viewDescriptions = {
                            __legacy__: generateLegacyLoadViewsResult(resModel, views, modelsCopy),
                            fields: models[resModel],
                            relatedModels: models,
                            views: {},
                        };
                        for (const viewType in views) {
                            const { arch, toolbar, id, filters, custom_view_id } = views[viewType];
                            const viewDescription = { arch, id, custom_view_id };
                            if (toolbar) {
                                viewDescription.actionMenus = toolbar;
                            }
                            if (filters) {
                                viewDescription.irFilters = filters;
                            }
                            viewDescriptions.views[viewType] = viewDescription;
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
