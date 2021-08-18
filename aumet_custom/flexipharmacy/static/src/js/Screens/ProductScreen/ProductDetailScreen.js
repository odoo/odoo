odoo.define('flexipharmacy.ProductDetailScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { debounce } = owl.utils;    
    var rpc = require('web.rpc');
    var core = require('web.core');


    class ProductDetailScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('close-screen', this.close);
            useListener('gride-view', this.view_product_id);
            useListener('list-view', this.view_list_product_id);
            useListener('search', this._onSearch);
            useListener('click-product', this.clickProductItem);
            this.state = {
                detailIsShown: this.env.pos.db.product_by_id,
                ShowListView: false,
                selectedProduct: this.product_by_id
            }
            this.searchDetails = {};
            this.selectedProductList = [];
            this.filter = null;
            this._initializeSearchFieldConstants();
            this.updateProductList = debounce(this.updateProductList, 70);
            $('button.grid').prop('active', true).addClass('highlight')
        }
        mounted() {
            this.env.pos.on('change:selectedCategoryId', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:selectedCategoryId', null, this);
        }
        get selectedCategoryId() {
            return 0;
        }
        get highlight() {
            return this.props.ProductId !== this.props.selectedview ? '' : 'highlight';
        }
        get imageUrl() {
            const product = this.product_by_id;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
        get pricelist(){
            const current_order = this.env.pos.get_order();
            if (current_order) {
                return current_order.pricelist;
            }
            return this.env.pos.default_pricelist;
        }
        get price(){
            const formattedUnitPrice = this.env.pos.format_currency(
                this.product_by_id.get_price(this.pricelist, 1),
                'Product Price'
            );
            if (this.product_by_id.to_weight) {
                return `${formattedUnitPrice}/${
                    this.env.pos.units_by_id[this.product_by_id.uom_id[0]].name
                }`;
            }else{
                return formattedUnitPrice;
            }
        }
        view_list_product_id(){
            this.state.ShowListView = true
            $('button.list').prop('active', true).addClass('highlight')
            $('button.grid').prop('active', false).removeClass('highlight')
            this.render();
        }
        view_product_id(){
            this.state.ShowListView = false
            $('button.grid').prop('active', true).addClass('highlight')
            $('button.list').prop('active', false).removeClass('highlight')
            this.render();
        }
        close(){
            this.showScreen('ProductScreen');
        }
        clickProductItem(event){
            if(this.selectedProductList.length > 0){
                if (this.selectedProductList.includes(event.detail)){
                    this.selectedProductList = _.without(this.selectedProductList, event.detail)
                }else{
                    this.selectedProductList.unshift(event.detail)
                }
            }else{
                this.selectedProductList.push(event.detail)
            }
            this.render();
        }
       async createNewPurchase(){
            var self = this
            const { confirmed, payload} = await this.showPopup('PurchaseOrderCreate', {
                title: this.env._t('Create Purcase Order'),
                SelectedProductList:this.selectedProductList,
                CreatedPurchaseOrder:'False',
            });
            if (confirmed) {
                if(!payload.partner_id){
                    this.env.pos.db.notification('danger',"Please select Supplier!");
                    return
                }
                var params = {
                    model: 'purchase.order',
                    method: 'pos_create_purchase_order',
                    args: ['', payload],
                }
                rpc.query(params, {async: false}).then(function(result){
                    if(result && result[0]){
                        var url = window.location.origin + '/web#id=' + result[0] + '&view_type=form&model=purchase.order';
                        const { confirmed, payload} = self.showPopup('PurchaseOrderCreate', {
                            title: self.env._t('Confirmation'),
                            SelectedProductList:[],
                            defination:'Purchase Order Created',
                            CreatedPurchaseOrder:'True',
                            order_name:result[1],
                            url:url,
                        });
                        self.selectedProductList = [];

                    }
                });
            }
        }
        // ========================================search Bar Product===============================
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        get productList() {
            var product_dict = {}
            if (this.searchDetails && this.searchDetails.searchTerm){
                product_dict = this.env.pos.db.product_by_id;
            }else{
                product_dict = this.env.pos.db.get_product_by_category(this.selectedCategoryId);
            }
            var product_by_id = $.map(product_dict, function(value, index){
                return [value];
            });
            return product_by_id;
        }
        get filteredProductList() {
            const filterCheck = (product) => {
                return true;
            };
            const { fieldValue, searchTerm } = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (product) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(product);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (product) => {
                return filterCheck(product) && searchCheck(product);
            }
            return this.productList.filter(predicate);
        }
        get searchBarProductConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }
        get filterOptions() {
            return ['All'];
        }
        get _searchFields() {
            var fields = {
                'Product Name': (product) => product.display_name,
                'Product Referance': (product) => product.default_code,
                'Product Category': (product) => product.pos_categ_id[1],
            };
            return fields;
        }
        /**
         * Maps the product screen params to product status.
         */
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
            });
        }
    }
    
    ProductDetailScreen.template = 'ProductDetailScreen';

    Registries.Component.add(ProductDetailScreen);

    return ProductDetailScreen;
});
