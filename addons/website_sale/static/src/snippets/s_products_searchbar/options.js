odoo.define('website_sale.s_products_searchbar_options', function (require) {
'use strict';

const Dialog = require('web.Dialog');
const options = require('web_editor.snippets.options');

const { qweb, _t } = require('web.core');

options.registry.ProductsSearchBar = options.Class.extend({
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.editor.xml'],

    /**
     * @override
     */
    start: function () {
        this.$searchProductsInput = this.$('.search-query');
        this.$searchOrderField = this.$('.o_wsale_search_order_by');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    openSearchbarSettings: function (previewMode, widgetValue, params) {
        var self = this;
        new Dialog(this, {
            title: _t("Products Search Bar"),
            $content: $(qweb.render('website_sale.dialog.productsSearchBar', {
                currentOrderBy: this.$searchOrderField.val(),
                currentLimit: parseInt(this.$searchProductsInput.attr('data-limit')),
                currentDisplayDescription: this.$searchProductsInput.attr('data-display-description') === 'true',
                currentDisplayPrice: this.$searchProductsInput.attr('data-display-price') === 'true',
                currentDisplayImage: this.$searchProductsInput.attr('data-display-image') === 'true',
            })),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    click: function () {
                        self.$searchOrderField.attr({
                            'value': this.$('#order_by').val(),
                        });
                        self.$searchProductsInput.attr({
                            'data-limit': this.$('#use_autocomplete').is(':checked') ? this.$('#limit').val() : 0,
                            'data-display-description': this.$('#display_description').is(':checked'),
                            'data-display-price': this.$('#display_price').is(':checked'),
                            'data-display-image': this.$('#display_image').is(':checked'),
                        });
                        self.$target.trigger('content_changed');
                        this.close();
                    },
                },
                {
                    text: _t("Discard"),
                    close: true,
                },
            ],
        }).open();
    },
});
});
