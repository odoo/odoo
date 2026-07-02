odoo.define('multi_vendor_marketplace.product_variants', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    
    publicWidget.registry.IndependentProductVariants = publicWidget.Widget.extend({
        selector: '.js_product',
        events: {
            'click .attribute-value-btn': '_onVariantButtonClick'
        },
        
        /**
         * Initialize the variant selection on page load
         */
        start: function () {
            this._super.apply(this, arguments);
            this._initializeVariants();
            return this;
        },
        
        /**
         * Select the first option for each attribute group initially
         */
        _initializeVariants: function () {
            var self = this;
            this.$('.product-attribute-group').each(function () {
                var $group = $(this);
                var $firstBtn = $group.find('.attribute-value-btn').first();
                if ($firstBtn.length) {
                    $firstBtn.addClass('selected');
                    
                    // Store the selected value in the hidden input
                    var attributeId = $firstBtn.data('attribute-id');
                    var valueId = $firstBtn.data('value-id');
                    self.$('#attribute_' + attributeId).val(valueId);
                }
            });
            
            // Update product information based on initial selection
            this._updateProductVariant();
        },
        
        /**
         * Handle click on variant buttons
         */
        _onVariantButtonClick: function (ev) {
            var $btn = $(ev.currentTarget);
            
            // Don't allow selecting disabled variants
            if ($btn.hasClass('disabled')) {
                return;
            }
            
            var attributeId = $btn.data('attribute-id');
            var valueId = $btn.data('value-id');
            
            // Remove 'selected' class from all buttons in this attribute group only
            this.$('.attribute-value-btn[data-attribute-id="' + attributeId + '"]').removeClass('selected');
            
            // Add 'selected' class to the clicked button
            $btn.addClass('selected');
            
            // Update hidden input with the selected value
            this.$('#attribute_' + attributeId).val(valueId);
            
            // Update product info based on new selection
            this._updateProductVariant();
        },
        
        /**
         * Update product information based on selected variants
         */
        _updateProductVariant: function () {
            // Collect all selected attributes
            var selectedAttributes = {};
            var self = this;
            
            this.$('.product-attribute-group').each(function () {
                var $group = $(this);
                var $selectedBtn = $group.find('.attribute-value-btn.selected');
                if ($selectedBtn.length) {
                    var attributeId = $selectedBtn.data('attribute-id');
                    var valueId = $selectedBtn.data('value-id');
                    selectedAttributes[attributeId] = parseInt(valueId, 10);
                }
            });
            
            // Update the product_id input
            var productId = this._findMatchingVariant(selectedAttributes);
            if (productId) {
                this.$('.product_id').val(productId);
                
                // Update price and other product details via AJAX
                this._updateProductDetails(productId);
            }
        },
        
        /**
         * Find the product variant that matches all selected attributes
         */
        _findMatchingVariant: function (selectedAttributes) {
            var variants = JSON.parse(this.$el.attr('data-product-variants') || '[]');
            var matchingVariant = null;
            
            for (var i = 0; i < variants.length; i++) {
                var variant = variants[i];
                var isMatch = true;
                
                // Check if this variant matches all selected attributes
                for (var attributeId in selectedAttributes) {
                    if (variant.attribute_values[attributeId] !== selectedAttributes[attributeId]) {
                        isMatch = false;
                        break;
                    }
                }
                
                if (isMatch) {
                    matchingVariant = variant;
                    break;
                }
            }
            
            return matchingVariant ? matchingVariant.id : null;
        },
        
        /**
         * Update product details (price, availability) via AJAX
         */
        _updateProductDetails: function (productId) {
            var self = this;
            ajax.jsonRpc('/shop/product/get_combination_info', 'call', {
                'product_id': productId,
                'add_qty': this.$('input[name="add_qty"]').val() || 1
            }).then(function (combinationInfo) {
                // Update price
                var $priceElement = self.$('.oe_price:first .oe_currency_value');
                if ($priceElement.length) {
                    $priceElement.text(self._formatCurrency(combinationInfo.price));
                }
                
                // Update availability message
                var $availabilityMessage = self.$('#availability_message');
                if ($availabilityMessage.length) {
                    if (combinationInfo.is_combination_possible) {
                        $availabilityMessage.removeClass('o_hidden').find('span').text('In Stock');
                    } else {
                        $availabilityMessage.removeClass('o_hidden').find('span').text('Out of Stock');
                    }
                }
            });
        },
        
        /**
         * Format a number as currency
         */
        _formatCurrency: function (price) {
            return price.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
        }
    });
    
    return publicWidget.registry.IndependentProductVariants;
});
