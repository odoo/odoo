odoo.define('website_sale_options.website_sale', function (require) {
    'use strict';
    
    var OptionalProductsModal = require('sale.OptionalProductsModal');
    var weContext = require('web_editor.context');
    var sAnimations = require('website.content.snippets.animation');
    require('website_sale.website_sale');
    
    var product_name_map = {};
    var optional_products_map = {};
    
    sAnimations.registry.WebsiteSaleOptions = sAnimations.Class.extend({
        selector: '.oe_website_sale',
        read_events: {
            'click #add_to_cart, #products_grid .product_price .a-submit': '_onClickAdd',
        },
    
        /**
         * @constructor
         */
        init: function () {
            this._super.apply(this, arguments);
    
            this._handleAdd = _.debounce(this._handleAdd.bind(this), 200, true);
        },
    
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
    
        /**
         * @private
         */
        _handleAdd: function ($form) {
            var self = this;
            var quantity = parseFloat($form.find('input[name="add_qty"]').val() || 1);
            var product_id = parseInt($form.find('input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked').first().val(),10);

            var modal = new OptionalProductsModal(quantity, product_id, $form, null, true);

            modal.on('options_empty', null, function () {
                $form.trigger('submit', [true]);
            });

            modal.on('back', null, function () {
                self._onModalSubmit($form);
            });

            modal.on('confirm', null, function () {
                self._onModalSubmit($form, true);
            });

            modal.on('modal_ready', null, function ($modal) {
                $modal.on('hidden.bs.modal', function () {
                    $form.removeClass('css_options'); // possibly reactivate opacity (see above)
                    $(this).remove();
                });
            });
            
            modal.appendTo($form);
        },

        _onModalSubmit: function($form, go_to_shop){
            $form.ajaxSubmit({
                url:  '/shop/cart/update_option',
                data: {lang: weContext.get().lang},
                success: function (quantity) {
                    if (go_to_shop) {
                        window.location.pathname = window.location.pathname.replace(/shop([\/?].*)?$/, "shop/cart");
                    }
                    var $q = $(".my_cart_quantity");
                    $q.parent().parent().removeClass("d-none", !quantity);
                    $q.html(quantity).hide().fadeIn(600);
                }
            });
        },
    
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
    
        _onClickAdd: function (ev) {
            ev.preventDefault();
            this._handleAdd($(ev.currentTarget).closest('form'));
        },
    });
    });
    