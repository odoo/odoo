/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

/**
 * SMART eCommerce Extension - Shop JavaScript
 */

// Delivery Zone Selection in Checkout
publicWidget.registry.SmartDeliveryZoneSelector = publicWidget.Widget.extend({
    selector: '.smart-delivery-zone-section',
    events: {
        'change .delivery-zone-radio': '_onZoneChange',
        'click .delivery-zone-option': '_onZoneOptionClick',
    },
    
    start: function () {
        var self = this;
        // Initialize with current selection
        var $checked = this.$('.delivery-zone-radio:checked');
        if ($checked.length) {
            this._updateZoneInfo($checked);
            $checked.closest('.delivery-zone-option').addClass('border-primary bg-light');
        }
        return this._super.apply(this, arguments);
    },
    
    _onZoneOptionClick: function (ev) {
        // IMPORTANT: Stop propagation to prevent Odoo checkout.js _changeAddress handler
        // from trying to call /shop/update_address without partner_id
        ev.stopPropagation();
        ev.preventDefault();
        
        // Allow clicking on the entire zone card to select it
        // Skip if click was on the radio itself
        if ($(ev.target).hasClass('delivery-zone-radio')) {
            return;
        }
        var $option = $(ev.currentTarget);
        var $radio = $option.find('.delivery-zone-radio');
        if (!$radio.is(':checked')) {
            $radio.prop('checked', true).trigger('change');
        }
    },
    
    _onZoneChange: function (ev) {
        // Stop propagation to prevent triggering Odoo checkout address change handlers
        ev.stopPropagation();
        
        var self = this;
        var $radio = $(ev.currentTarget);
        var zoneId = $radio.val();
        
        // Update visual selection
        this.$('.delivery-zone-option').removeClass('border-primary bg-light');
        $radio.closest('.delivery-zone-option').addClass('border-primary bg-light');
        
        // Update info display
        this._updateZoneInfo($radio);
        
        // Send to server via JSON RPC
        rpc('/shop/set_delivery_zone', {
            zone_id: parseInt(zoneId)
        }).then(function (result) {
            if (result.success) {
                // Update any displayed delivery cost
                if (result.delivery_price !== undefined) {
                    self.$('#selected_zone_price').text(result.delivery_price_formatted || result.delivery_price);
                }
                // Update the cart summary totals if provided
                if (result.amounts) {
                    var amounts = result.amounts;
                    // Delivery row
                    $('#message_no_dm_set').addClass('d-none');
                    $('#order_delivery .monetary_field').removeClass('d-none').text(amounts.delivery_formatted || amounts.delivery);
                    // Subtotal, taxes, total
                    $('#order_total_untaxed .monetary_field').text(amounts.untaxed_formatted || amounts.untaxed);
                    $('#order_total_taxes .monetary_field').text(amounts.tax_formatted || amounts.tax);
                    $('#order_total .monetary_field').text(amounts.total_formatted || amounts.total);
                    $('#amount_total_summary').text(amounts.total_formatted || amounts.total);
                }
                // Show success message
                self._showMessage('Delivery zone updated successfully', 'success');
            } else {
                self._showMessage(result.error || 'Failed to update delivery zone', 'error');
            }
        }).catch(function (error) {
            console.error('Failed to set delivery zone:', error);
            self._showMessage('Failed to update delivery zone', 'error');
        });
    },
    
    _updateZoneInfo: function ($radio) {
        var $option = $radio.closest('.delivery-zone-option');
        var zoneName = $option.data('zone-name') || $option.find('strong').first().text();
        var zonePrice = $option.data('zone-price');
        var zoneDays = $option.data('zone-days');
        
        this.$('#delivery_zone_info').removeClass('d-none');
        this.$('#selected_zone_name').text(zoneName);
        if (zonePrice) {
            this.$('#selected_zone_price').text(zonePrice);
        }
        if (zoneDays) {
            this.$('#selected_zone_days').text(zoneDays);
        }
    },
    
    _showMessage: function (message, type) {
        // Remove any existing alerts
        this.$('.alert-smart').remove();
        
        var alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        var $alert = $('<div class="alert ' + alertClass + ' alert-dismissible fade show mt-2 alert-smart" role="alert">' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
            '</div>');
        
        this.$('.delivery-zone-options').after($alert);
        
        // Auto-dismiss after 3 seconds
        setTimeout(function () {
            $alert.fadeOut(function () {
                $(this).remove();
            });
        }, 3000);
    }
});

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
        rpc('/shop/delivery_estimate', {
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

// Cart Delivery Zone Dropdown
publicWidget.registry.SmartCartDeliveryZone = publicWidget.Widget.extend({
    selector: '.smart-cart-delivery-zone',
    events: {
        'change .delivery-zone-select': '_onZoneSelect',
    },
    
    _onZoneSelect: function (ev) {
        var zoneId = $(ev.currentTarget).val();
        if (zoneId) {
            rpc('/shop/set_delivery_zone', {
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
        border-color: #714B67 !important;
    }
`;
document.head.appendChild(style);

export default {
    SmartDeliveryZoneSelector: publicWidget.registry.SmartDeliveryZoneSelector,
    SmartDeliveryEstimate: publicWidget.registry.SmartDeliveryEstimate,
    SmartProductCardHover: publicWidget.registry.SmartProductCardHover,
    SmartStockBadge: publicWidget.registry.SmartStockBadge,
    SmartCartDeliveryZone: publicWidget.registry.SmartCartDeliveryZone,
    SmartCategoryCard: publicWidget.registry.SmartCategoryCard,
};
