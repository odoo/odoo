/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * This service is comprised of 2 commands that are interacting with embeddedFilters which is
 * the object that will store the different filters of the embedded views.
 *
 * @function saveFilters This function is used to save the filters for a specific embedId.
 * @function applyFilter This function adds the correct filter to the view's props.
 */
export const knowledgeEmbedViewsFilters = {
    start(env) {
        const embeddedFilters = {};
        const commands = {
            /**
             * @param {*} currentController The current controller returned by the action service
             * @param {String} filterKey The ID of the impacted embedded view
             * @param {Object} searchModel The searchModel for the view's props that will be saved
             * inside the embeddedFilters Object.
             */
            saveFilters: (currentController, filterKey, searchModel) => {
                if (!embeddedFilters[filterKey]) {
                    embeddedFilters[filterKey] = {};
                }
                embeddedFilters[filterKey][currentController.jsId] = searchModel;
            },
            /**
             * This function applies the previously saved filters to the view's props.
             * Each time that we apply filters to a view we remove the filter that we apply in order to
             * avoid collisions and to avoid applying the filters when we change articles in Knowledge
             * (which should not add filters to the embedded view).
             *
             * When we come back to the root of the breadcrumbs, we remove all the filters for the specific
             * embed view in order to not store useless filters and to avoid collisions with filters that
             * weren't applied to the view.
             * This way we ensure that filters are either applied once or never, if the corresponding breadcrumb has
             * not been opened.
             * @param {*} currentController The current controller given by the action service
             * @param {String} filterKey The key used to get the filters of a specific embedded view
             * @param {*} ViewProps The embedded view's props that will be updated with the filters
             */
            applyFilter: (currentController, filterKey, ViewProps) => {
                const currentJsId = currentController.jsId;
                const embedSearchFilters = embeddedFilters[filterKey];

                if (embedSearchFilters && embedSearchFilters[currentJsId]) {
                    ViewProps.globalState.searchModel = embeddedFilters[filterKey][currentJsId];
                    delete embeddedFilters[filterKey][currentJsId];
                }

                if (currentController.config.breadcrumbs.length === 1) {
                    delete embeddedFilters[filterKey];
                }
            }
        };
        return commands;
    }
};

registry.category("services").add("knowledgeEmbedViewsFilters", knowledgeEmbedViewsFilters);
