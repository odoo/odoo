odoo.define('flexipharmacy.MaterialMonitorControlPanel', function(require) {
    'use strict';

    const { useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class MaterialMonitorControlPanel extends PosComponent {
        constructor() {
            super(...arguments);
            this.searchWordInput = useRef('search-word-input');
            this.updateSearch = debounce(this.updateSearch, 100);
            useListener('click-product-category', this.OpenProductCategory);
        }
        clearSearch() {
            this.searchWordInput.el.value = '';
            this.trigger('clear-search');
        }
        updateSearch(event) {
            this.trigger('update-search', event.target.value);
            if (event.key === 'Enter') {
                // We are passing the searchWordInput ref so that when necessary,
                // it can be modified by the parent.
                this.trigger('try-add-product', { searchWordInput: this.searchWordInput });
            }
        }
        OpenProductCategory(){
            this.state.expanded = !this.state.expanded
        }
        get selectedMaterialCategoryId() {
            return this.env.pos.get('selectedMaterialCategoryId');
        }
        get breadcrumbs() {
            if (this.selectedMaterialCategoryId === this.env.pos.db.root_category_id) return [];
            return [
                ...this.env.pos.db
                    .get_category_ancestors_ids(this.selectedMaterialCategoryId)
                    .slice(1),
                this.selectedMaterialCategoryId,
            ].map(id => this.env.pos.db.get_category_by_id(id)).slice(-1)[0];
        }
        get subcategories() {
            return this.env.pos.db.get_category_childs_ids(this.selectedMaterialCategoryId)
                .map(id => this.env.pos.db.get_category_by_id(id));
        }
        get selectedCategory(){
            if (this.selectedMaterialCategoryId === this.env.pos.db.root_category_id) return [];
            return this.env.pos.db.get_category_by_id(this.selectedMaterialCategoryId)
        }
    }
    MaterialMonitorControlPanel.template = 'MaterialMonitorControlPanel';

    Registries.Component.add(MaterialMonitorControlPanel);

    return MaterialMonitorControlPanel;
});
