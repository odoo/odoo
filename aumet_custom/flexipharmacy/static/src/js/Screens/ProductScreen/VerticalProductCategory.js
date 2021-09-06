    odoo.define('flexipharmacy.VerticalProductCategory', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState, useExternalListener } = owl.hooks;

    class VerticalProductCategory extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ expanded: false });
            useListener('click-product-category', this.OpenProductCategory);
            useExternalListener(window, 'click', this._hideVerticalCategory);
        }
        _hideVerticalCategory(event){
            if (!$(event.target).attr('class') ){
                if($(event.target).html() !== 'CATEGORY'){
                    this.state.expanded = false
                }
            }else{
                if($(event.target).attr('class') === 'vertical-category-button' || $(event.target).attr('class') === 'VerticalCategoryTitle'){
                    this.state.expanded = !this.state.expanded
                }else if($(event.target).attr('class') === 'vertical-category' || $(event.target).attr('class') === 'category-simple-button'  || $(event.target).attr('class') === 'fa fa-home' || $(event.target).attr('class') === 'category-simple-button active' || $(event.target).attr('class') === 'breadcrumb-button breadcrumb-home'){
                    this.state.expanded = true
                }else{
                    this.state.expanded = false
                }
            }
        }
        OpenProductCategory(){
            this.state.expanded = !this.state.expanded
        }
        get selectedCategoryId() {
            return this.env.pos.get('selectedCategoryId');
        }
        get breadcrumbs() {
            if (this.selectedCategoryId === this.env.pos.db.root_category_id) return [];
            return [
                ...this.env.pos.db
                    .get_category_ancestors_ids(this.selectedCategoryId)
                    .slice(1),
                this.selectedCategoryId,
            ].map(id => this.env.pos.db.get_category_by_id(id)).slice(-1)[0];
        }
        get subcategories() {
            return this.env.pos.db.get_category_childs_ids(this.selectedCategoryId)
                .map(id => this.env.pos.db.get_category_by_id(id));
        }
        get selectedCategory(){
            if (this.selectedCategoryId === this.env.pos.db.root_category_id) return [];
            return this.env.pos.db.get_category_by_id(this.selectedCategoryId)
        }
    }
    VerticalProductCategory.template = 'VerticalProductCategory';

    Registries.Component.add(VerticalProductCategory);

    return VerticalProductCategory;
});
