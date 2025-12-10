/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * SMART eCommerce Extension - Shop JavaScript
 */

// Delivery Estimate Widget
publicWidget.registry.SmartDeliveryEstimate = publicWidget.Widget.extend({
    selector: '.smart-delivery-estimate',
    
    start: function () {
        var self = this;
        var $deliveryText = this.$('.delivery-date-text');
        var productId = $deliveryText.data('product-id');
        
        if (!productId) {
            $deliveryText.text('Contact us for delivery info');
            return this._super.apply(this, arguments);
        }
        
        // Get user's city from session or prompt
        var city = this._getUserCity();
        
        // Fetch delivery estimate
        jsonrpc('/shop/delivery_estimate', {
            product_id: productId,
            city: city
        }).then(function (result) {
            if (result.error) {
                $deliveryText.text('Delivery info unavailable');
            } else if (result.estimate) {
                var text = result.estimate.formatted;
                if (result.zone) {
                    text += ' (' + result.zone.name + ')';
                }
                $deliveryText.text(text);
                
                // Add zone price if available
                if (result.zone && result.zone.price > 0) {
                    self.$el.append(
                        '<div class="mt-1 small text-muted">' +
                        '<i class="fa fa-info-circle me-1"></i>' +
                        'Delivery from ' + result.zone.currency + result.zone.price +
                        '</div>'
                    );
                }
            }
        }).catch(function () {
            $deliveryText.text('Check delivery at checkout');
        });
        
        return this._super.apply(this, arguments);
    },
    
    _getUserCity: function () {
        // Try to get city from various sources
        // 1. Session storage (previous selection)
        var city = sessionStorage.getItem('smart_delivery_city');
        if (city) return city;
        
        // 2. URL parameter
        var urlParams = new URLSearchParams(window.location.search);
        city = urlParams.get('city');
        if (city) {
            sessionStorage.setItem('smart_delivery_city', city);
            return city;
        }
        
        // 3. Default (can be enhanced with geolocation)
        return null;
    }
});

// Product Card Hover Enhancement
publicWidget.registry.SmartProductCardHover = publicWidget.Widget.extend({
    selector: '.smart-product-image-wrapper',
    events: {
        'mouseenter': '_onMouseEnter',
        'mouseleave': '_onMouseLeave',
    },
    
    _onMouseEnter: function () {
        this.$('.smart-hover-image').addClass('active');
    },
    
    _onMouseLeave: function () {
        this.$('.smart-hover-image').removeClass('active');
    }
});

// Price Range Filter Enhancement
publicWidget.registry.SmartPriceRangeFilter = publicWidget.Widget.extend({
    selector: '#collapse_price_range',
    events: {
        'input input[name="price_min"]': '_onPriceInput',
        'input input[name="price_max"]': '_onPriceInput',
    },
    
    _onPriceInput: function (ev) {
        var $input = $(ev.currentTarget);
        var value = parseFloat($input.val()) || 0;
        var min = parseFloat($input.attr('min')) || 0;
        var max = parseFloat($input.attr('max')) || Infinity;
        
        // Clamp value
        if (value < min) $input.val(min);
        if (value > max) $input.val(max);
        
        // Update visual feedback
        this._updatePriceDisplay();
    },
    
    _updatePriceDisplay: function () {
        var minVal = this.$('input[name="price_min"]').val() || '0';
        var maxVal = this.$('input[name="price_max"]').val() || '∞';
        
        // Could update a display element here
        console.log('Price range: ' + minVal + ' - ' + maxVal);
    }
});

// City Selection for Delivery Estimate
publicWidget.registry.SmartCitySelector = publicWidget.Widget.extend({
    selector: '.smart-city-selector',
    events: {
        'change select': '_onCityChange',
    },
    
    _onCityChange: function (ev) {
        var city = $(ev.currentTarget).val();
        if (city) {
            sessionStorage.setItem('smart_delivery_city', city);
            
            // Refresh delivery estimates on page
            $('.delivery-date-text').each(function () {
                var $el = $(this);
                var productId = $el.data('product-id');
                if (productId) {
                    $el.text('Updating...');
                    jsonrpc('/shop/delivery_estimate', {
                        product_id: productId,
                        city: city
                    }).then(function (result) {
                        if (result.estimate) {
                            $el.text(result.estimate.formatted);
                        }
                    });
                }
            });
        }
    }
});

// Stock Badge Animation
publicWidget.registry.SmartStockBadge = publicWidget.Widget.extend({
    selector: '.smart-stock-badge',
    
    start: function () {
        // Add pulse animation for low stock items
        if (this.$el.hasClass('text-bg-warning')) {
            this.$el.addClass('animate-pulse');
        }
        return this._super.apply(this, arguments);
    }
});

// Delivery Zone Selection in Checkout
publicWidget.registry.SmartDeliveryZoneSelector = publicWidget.Widget.extend({
    selector: '.smart-delivery-zone-section',
    events: {
        'change .delivery-zone-radio': '_onZoneChange',
    },
    
    start: function () {
        var self = this;
        // Initialize with current selection
        var $checked = this.$('.delivery-zone-radio:checked');
        if ($checked.length) {
            this._updateZoneInfo($checked);
        }
        return this._super.apply(this, arguments);
    },
    
    _onZoneChange: function (ev) {
        var self = this;
        var $radio = $(ev.currentTarget);
        var zoneId = $radio.val();
        
        // Update visual selection
        this.$('.delivery-zone-option').removeClass('border-primary bg-light');
        $radio.closest('.delivery-zone-option').addClass('border-primary bg-light');
        
        // Update info display
        this._updateZoneInfo($radio);
        
        // Send to server
        jsonrpc('/shop/set_delivery_zone', {
            zone_id: parseInt(zoneId)
        }).then(function (result) {
            if (result.success) {
                // Update any displayed delivery cost
                if (result.delivery_price !== undefined) {
                    self.$('#selected_zone_price').text(result.delivery_price_formatted || result.delivery_price);
                }
                // Optionally reload to update totals
                // window.location.reload();
            }
        }).catch(function (error) {
            console.error('Failed to set delivery zone:', error);
        });
    },
    
    _updateZoneInfo: function ($radio) {
        var $option = $radio.closest('.delivery-zone-option');
        var zoneName = $option.find('strong').first().text();
        var zonePrice = $option.data('zone-price');
        var zoneDays = $option.data('zone-days');
        
        this.$('#delivery_zone_info').removeClass('d-none');
        this.$('#selected_zone_name').text(zoneName);
        this.$('#selected_zone_price').text(zonePrice);
        this.$('#selected_zone_days').text(zoneDays);
    }
});

// Cart Delivery Zone Dropdown
publicWidget.registry.SmartCartDeliveryZone = publicWidget.Widget.extend({
    selector: '.smart-cart-delivery-zone',
    events: {
        'change .delivery-zone-select': '_onZoneSelect',
    },
    
    _onZoneSelect: function (ev) {
        var zoneId = $(ev.currentTarget).val();
        if (zoneId) {
            jsonrpc('/shop/set_delivery_zone', {
                zone_id: parseInt(zoneId)
            }).then(function (result) {
                if (result.success) {
                    // Reload page to update cart totals
                    window.location.reload();
                }
            });
        }
    }
});

// Homepage Category Cards Hover Effect
publicWidget.registry.SmartCategoryCard = publicWidget.Widget.extend({
    selector: '.smart-category-card, .smart-category-card-mobile',
    events: {
        'mouseenter': '_onMouseEnter',
        'mouseleave': '_onMouseLeave',
    },
    
    _onMouseEnter: function () {
        this.$el.addClass('shadow-lg').css('transform', 'translateY(-5px)');
    },
    
    _onMouseLeave: function () {
        this.$el.removeClass('shadow-lg').css('transform', 'translateY(0)');
    }
});

// Add CSS animation dynamically
var style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    .animate-pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    .smart-category-card, .smart-category-card-mobile {
        transition: all 0.3s ease;
    }
    .delivery-zone-option {
        transition: all 0.2s ease;
        cursor: pointer;
    }
    .delivery-zone-option:hover {
        border-color: #714B67 !important;
        background-color: #f8f9fa;
    }
    .delivery-zone-option.border-primary {
        border-width: 2px !important;
    }
`;
document.head.appendChild(style);

export default {
    SmartDeliveryEstimate: publicWidget.registry.SmartDeliveryEstimate,
    SmartProductCardHover: publicWidget.registry.SmartProductCardHover,
    SmartPriceRangeFilter: publicWidget.registry.SmartPriceRangeFilter,
    SmartCitySelector: publicWidget.registry.SmartCitySelector,
    SmartStockBadge: publicWidget.registry.SmartStockBadge,
    SmartDeliveryZoneSelector: publicWidget.registry.SmartDeliveryZoneSelector,
    SmartCartDeliveryZone: publicWidget.registry.SmartCartDeliveryZone,
    SmartCategoryCard: publicWidget.registry.SmartCategoryCard,
};

