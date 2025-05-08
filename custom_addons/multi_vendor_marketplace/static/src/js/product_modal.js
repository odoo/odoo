odoo.define('multi_vendor_marketplace.product_modal', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var _t = core._t;

    publicWidget.registry.ProductModal = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: {
            'click .o_show_variants_modal': '_onShowVariantsModal',
            'click .modal-buy-now': '_onModalBuyNow',
            'click #modal_add_to_cart': '_onModalAddToCart',
            'click .js_qty_modal_plus': '_onModalChangeQuantity',
            'click .js_qty_modal_minus': '_onModalChangeQuantity',
        },

        /**
         * @override
         */
        start: function () {
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Открыть модальное окно для выбора вариантов товара
         *
         * @private
         * @param {Event} ev
         */
        _onShowVariantsModal: function (ev) {
            var $modal = $('#product_variants_modal');
            $modal.modal('show');
            
            // Сохраняем кнопку, которая была нажата (Buy Now или Add to Cart)
            var action = $(ev.currentTarget).hasClass('o_buy_now') ? 'buy_now' : 'add_to_cart';
            $modal.data('action', action);
        },

        /**
         * Обработка нажатия на кнопку "Buy Now" в модальном окне
         *
         * @private
         * @param {Event} ev
         */
        _onModalBuyNow: function (ev) {
            this._processModalSelection('buy_now');
        },

        /**
         * Обработка нажатия на кнопку "Add to Cart" в модальном окне
         *
         * @private
         * @param {Event} ev
         */
        _onModalAddToCart: function (ev) {
            this._processModalSelection('add_to_cart');
        },

        /**
         * Обработка изменения количества в модальном окне
         *
         * @private
         * @param {Event} ev
         */
        _onModalChangeQuantity: function (ev) {
            ev.preventDefault();
            var $input = $('.quantity_modal');
            var qty = parseInt($input.val() || '0', 10);
            if ($(ev.currentTarget).hasClass('js_qty_modal_plus')) {
                $input.val(qty + 1);
            } else {
                if (qty > 1) {
                    $input.val(qty - 1);
                }
            }
        },

        /**
         * Обработка выбора вариантов и отправка формы
         *
         * @private
         * @param {String} action - 'buy_now' или 'add_to_cart'
         */
        _processModalSelection: function (action) {
            var $modal = $('#product_variants_modal');
            var $form = $('form[action="/shop/cart/update"]');
            
            // Получаем выбранное количество из модального окна
            var qty = parseInt($('.quantity_modal').val() || '1', 10);
            $('input[name="add_qty"]').val(qty);
            
            // Обрабатываем выбранные атрибуты
            var attributes = {};
            $('.form-check-input:checked').each(function() {
                var name = $(this).attr('name');
                var value = $(this).val();
                attributes[name] = value;
            });
            
            // Добавляем кнопку buy_now если нужно
            if (action === 'buy_now') {
                if (!$form.find('input[name="express"]').length) {
                    $form.append('<input type="hidden" name="express" value="1"/>');
                }
            } else {
                $form.find('input[name="express"]').remove();
            }
            
            // Закрываем модальное окно
            $modal.modal('hide');
            
            // Отправляем форму
            $form.submit();
        }
    });

    return publicWidget.registry.ProductModal;
});

odoo.define('multi_vendor_marketplace.buy_now_button', function (require) {
    'use strict';
    
    var publicWidget = require('web.public.widget');
    
    publicWidget.registry.BuyNowButton = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: {
            'click .o_we_buy_now': '_onBuyNowClick',
        },
        _onBuyNowClick: function (ev) {
            var $btn = $(ev.currentTarget);
            var $form = $btn.closest('form');
            if ($form.length) {
                // Add express=1 if not present
                if ($form.find('input[name="express"]').length === 0) {
                    $('<input>').attr({type: 'hidden', name: 'express', value: '1'}).appendTo($form);
                }
                $form.submit();
            }
        }
    });
});

// Quantity control for product detail page
odoo.define('multi_vendor_marketplace.product_qty_control', function (require) {
    $(document).ready(function () {
        $(document).on('click', '.js_add_qty', function () {
            var $input = $(this).closest('.input-group').find('.js_quantity');
            var val = parseInt($input.val()) || 1;
            $input.val(val + 1).trigger('change');
        });
        $(document).on('click', '.js_remove_qty', function () {
            var $input = $(this).closest('.input-group').find('.js_quantity');
            var val = parseInt($input.val()) || 1;
            if (val > 1) {
                $input.val(val - 1).trigger('change');
            }
        });
    });
}); 