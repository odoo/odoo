/** @odoo-module **/

import { SearchModel } from "@web/search/search_model";

export const KnowledgeSearchModelMixin = (T) => class extends T {
    setup(services, args) {
        this.saveEmbeddedViewFavoriteFilter = args.saveEmbeddedViewFavoriteFilter;
        this.deleteEmbeddedViewFavoriteFilter = args.deleteEmbeddedViewFavoriteFilter;
        super.setup(services, args);
    }

    /**
     * Favorites for embedded views
     * @override
     */
    async load(config) {
        await super.load(config);
        if (config.state && !this.isStateCompleteForEmbeddedView) {
            // If the config contains an imported state that is not directly
            // coming from a view that was embedded in Knowledge, the favorite
            // filters have to be loaded, since they come from the
            // `data-embedded-props` attribute of the anchor for the
            // EmbeddedViewComponent. Otherwise, those are already specified in
            // the state and they should not be duplicated.
            let defaultFavoriteId = null;
            const activateFavorite = "activateFavorite" in config ? config.activateFavorite : true;
            if (activateFavorite) {
                defaultFavoriteId = this._createGroupOfFavorites(this.irFilters || []);
                if (defaultFavoriteId) {
                    // activate default search items (populate this.query)
                    this._activateDefaultSearchItems(defaultFavoriteId);
                }
            }
        }
    }

    /**
     * Save in embedded view arch instead of creating a record
     * @override
     */
    async _createIrFilters(irFilter) {
        this.saveEmbeddedViewFavoriteFilter(irFilter);
        return null;
    }

    /**
     * Delete from the embedded view arch instead of deleting the record
     * @override
     */
    async _deleteIrFilters(searchItem) {
        this.deleteEmbeddedViewFavoriteFilter(searchItem);
    }

    /**
     * @override
     * @returns {Object}
     */
    exportState() {
        const state = super.exportState();
        state.isStateCompleteForEmbeddedView = true;
        return state;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(state);
        this.isStateCompleteForEmbeddedView = state.isStateCompleteForEmbeddedView;
    }
};

export class KnowledgeSearchModel extends KnowledgeSearchModelMixin(SearchModel) {}
