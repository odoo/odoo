/** @odoo-module **/
import { serviceRegistry } from "../webclient/service_registry";

/**
 * @typedef {Object} Fields
 */

/**
 * @typedef {string} ViewType // to define
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
 * @property {Fields} fields
 * @property {ViewType} type
 * @property {number} view_id
 * @property {IrFilter[]} [irFilters]
 */

/**
 * @typedef {Object} LoadViewsParams
 * @property {string} model
 * @property {[number, ViewType][]} views
 * @property {Object} context
 */

/**
 * @typedef {Object} LoadViewsOptions
 * @property {number} actionId
 * @property {boolean} withActionMenus
 * @property {boolean} withFilters
 */

export const viewService = {
  name: "view",
  dependencies: ["orm"],
  deploy(env) {
    const { orm } = env.services;
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
      const key = JSON.stringify([params.model, params.views, params.context, options]);
      if (!cache[key]) {
        const result = await orm.call(params.model, "load_views", [], {
          views: params.views,
          options: {
            action_id: options.actionId || false,
            load_filters: options.withFilters || false,
            toolbar: options.withActionMenus || false,
          },
          context: params.context,
        });
        const viewDescriptions = result; // for legacy purpose, keys in result are left in viewDescriptions

        for (const [_, viewType] of params.views) {
          const viewDescription = result.fields_views[viewType];
          viewDescription.fields = Object.assign({}, result.fields, viewDescription.fields); // before a deep freeze was done.
          if (viewType === "search" && options.withFilters) {
            viewDescription.irFilters = result.filters;
          }
          viewDescriptions[viewType] = viewDescription;
        }

        cache[key] = viewDescriptions;
      }
      return cache[key];
    }
    return { loadViews };
  },
};

serviceRegistry.add("view", viewService);
