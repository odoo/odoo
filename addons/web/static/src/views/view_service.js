import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { UPDATE_METHODS } from "@web/core/orm_service";
import { session } from "@web/session";

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
    dependencies: ["disk_cache", "orm"],
    async start(env, { disk_cache: diskCache, orm }) {
        diskCache.defineTable(
            "views",
            session.cache_hashes.templates_cache,
            (resModel, views, context, options) => {
                return orm
                    .call(resModel, "get_views", [], {
                        context,
                        views,
                        options,
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
                    });
            },
            (...args) => JSON.stringify(args)
        );
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { model, method } = ev.detail.data.params;
            if (["ir.ui.view", "ir.filters"].includes(model)) {
                if (UPDATE_METHODS.includes(method) || method === "create_or_replace") {
                    diskCache.invalidate("views");
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
            return diskCache.read("views", resModel, views, filteredContext, loadViewsOptions);
        }
        return { loadViews };
    },
};

registry.category("services").add("view", viewService);
