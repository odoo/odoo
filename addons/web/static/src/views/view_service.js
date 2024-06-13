import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { UPDATE_METHODS } from "@web/core/orm_service";

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
 * @property {number | false} embedded_action_id
 * @property {number | false} embedded_parent_res_id
 */

/**
 * @typedef {Object} ViewDescription
 * @property {string} arch
 * @property {number|false} id
 * @property {number|null} [custom_view_id]
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

        function clearCache() {
            cache = {};
            const processedArchs = registry.category("__processed_archs__");
            processedArchs.content = {};
            processedArchs.trigger("UPDATE");
        }

        env.bus.addEventListener("CLEAR-CACHES", clearCache);
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { model, method } = ev.detail.data.params;
            if (["ir.ui.view", "ir.filters"].includes(model)) {
                if (UPDATE_METHODS.includes(method)) {
                    clearCache();
                }
            }
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
            const { context, resModel, views } = params;
            const loadViewsOptions = {
                action_id: options.actionId || false,
                embedded_action_id: options.embeddedActionId || false,
                embedded_parent_res_id: options.embeddedParentResId || false,
                load_filters: options.loadIrFilters || false,
                toolbar: (!context?.disable_toolbar && options.loadActionMenus) || false,
            };
            for (const key in options) {
                if (
                    ![
                        "actionId",
                        "embeddedActionId",
                        "embeddedParentResId",
                        "loadIrFilters",
                        "loadActionMenus",
                    ].includes(key)
                ) {
                    loadViewsOptions[key] = options[key];
                }
            }
            if (env.isSmall) {
                loadViewsOptions.mobile = true;
            }
            const filteredContext = Object.fromEntries(
                Object.entries(context || {}).filter(
                    ([k, v]) => k == "lang" || k.endsWith("_view_ref")
                )
            );

            const key = JSON.stringify([resModel, views, filteredContext, loadViewsOptions]);
            if (!cache[key]) {
                cache[key] = orm
                    .call(resModel, "get_views", [], {
                        context: filteredContext,
                        views,
                        options: loadViewsOptions,
                    })
                    .then((result) => {
                        const { models, views } = result;
                        const viewDescriptions = {
                            fields: models[resModel].fields,
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
