    odoo.define('flexipharmacy.MaterialMonitordetail', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    
    class MaterialMonitordetail extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('switch-category', this._switchCategory);
            useListener('update-search', this._updateSearch);
            useListener('try-add-product', this._tryAddProduct);
            useListener('clear-search', this._clearSearch);
            this.state = useState({ searchWord: '' });
        }
        mounted() {
            this.env.pos.on('change:selectedMaterialCategoryId', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:selectedMaterialCategoryId', null, this);
        }
        get selectedMaterialCategoryId() {
            return this.env.pos.get('selectedMaterialCategoryId');
        }
        get searchWord() {
            return this.state.searchWord.trim();
        }
        get materialToDisplay() {
            if (this.searchWord !== '') {
                return this.env.pos.db.search_product_in_category(
                    this.selectedMaterialCategoryId,
                    this.searchWord
                ).filter(product => product.is_material_monitor);
            } else {
                return this.env.pos.db.get_product_by_category(this.selectedMaterialCategoryId).filter(product => product.is_material_monitor);
            }
        }
        get subcategories() {
            return this.env.pos.db
                .get_category_childs_ids(this.selectedMaterialCategoryId)
                .map(id => this.env.pos.db.get_category_by_id(id));
        }
        get breadcrumbs() {
            if (this.selectedMaterialCategoryId === this.env.pos.db.root_category_id) return [];
            return [
                ...this.env.pos.db
                    .get_category_ancestors_ids(this.selectedMaterialCategoryId)
                    .slice(1),
                this.selectedMaterialCategoryId,
            ].map(id => this.env.pos.db.get_category_by_id(id));
        }
        get hasNoCategories() {
            return this.env.pos.db.get_category_childs_ids(0).length === 0;
        }
        _switchCategory(event) {
            this.env.pos.set('selectedMaterialCategoryId', event.detail);
        }
        _updateSearch(event) {
            this.state.searchWord = event.detail;
        }
        _tryAddProduct(event) {
            const searchResults = this.materialToDisplay;
            // If the search result contains one item, add the product and clear the search.
            if (searchResults.length === 1) {
                const { searchWordInput } = event.detail;
                this.trigger('click-product', searchResults[0]);
                // the value of the input element is not linked to the searchWord state,
                // so we clear both the state and the element's value.
                searchWordInput.el.value = '';
                this._clearSearch();
            }
        }
        _clearSearch() {
            this.state.searchWord = '';
        }
    }
    MaterialMonitordetail.template = 'MaterialMonitordetail';

    Registries.Component.add(MaterialMonitordetail);

    return MaterialMonitordetail;
});
