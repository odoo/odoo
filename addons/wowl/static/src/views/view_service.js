/** @odoo-module **/

export const viewService = {
  name: "view",
  dependencies: ["model"],
  deploy(env) {
    const modelService = env.services.model;
    const cache = {};
    /**
     * Loads various information concerning views: fields_view for each view,
     * fields of the corresponding model, and optionally the filters.
     *
     * @param {params} LoadViewsParams
     * @param {options} LoadViewsOptions
     * @returns {Promise<ViewDescriptions>}
     */
    async function loadViews(params, options) {
      const key = JSON.stringify([params.model, params.views, params.context, options]);
      if (!cache[key]) {
        cache[key] = modelService(params.model)
          .call("load_views", [], {
            views: params.views,
            options: {
              action_id: options.actionId || false,
              load_filters: options.withFilters || false,
              toolbar: options.withActionMenus || false,
            },
            context: params.context,
          })
          .then((result) => {
            const viewDescriptions = result; // we add keys in result for legacy! ---> c'est moche!
            for (const [_, viewType] of params.views) {
              const viewDescription = result.fields_views[viewType];
              viewDescription.fields = Object.assign({}, result.fields, viewDescription.fields); // before a deep freeze was done.
              if (viewType === "search" && options.withFilters) {
                viewDescription.irFilters = result.filters;
              }
              viewDescriptions[viewType] = viewDescription;
            }
            return viewDescriptions;
          });
      }
      return await cache[key]; // FIXME: clarify the API --> already better but ...
    }
    return { loadViews };
  },
};
