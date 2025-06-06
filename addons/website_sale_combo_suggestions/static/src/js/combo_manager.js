/* global $ */
(function () {
    'use strict';

    const ComboManager = {
        init() {
            $(document).ready(() => {
                if (window.location.pathname === '/shop/cart') {
                    setTimeout(() => {
                        this.checkForCombos();
                        this.initCartObserver();
                    }, 300);
                }
            });
        },

        formatCurrency(amount, symbol, position) {
            const formatted = parseFloat(amount).toFixed(2);
            return position === 'before'
                ? `${symbol}${formatted}`
                : `${formatted}${symbol}`;
        },

        getTranslation(trans, key, fallback) {
            return (trans && trans[key]) ? trans[key] : fallback;
        },

        getCsrfToken() {
            if (typeof odoo !== 'undefined' && odoo.csrf_token) {
                return odoo.csrf_token;
            }
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            return metaTag ? metaTag.getAttribute('content') : null;
        },

        initCartObserver() {
            const cartContainer = document.querySelector('.oe_cart');
            if (!cartContainer) {
                return;
            }
            const observer = new MutationObserver(() => {
                clearTimeout(window.comboCheckTimeout);
                window.comboCheckTimeout = setTimeout(() => {
                    this.recalculateAllCombos();
                }, 1500);
            });
            observer.observe(cartContainer, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class'],
            });
        },

        async recalculateAllCombos() {
            $('.simple-combo-alert').remove();
            try {
                const response = await fetch('/shop/recalculate_combos', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    body: JSON.stringify({}),
                });
                const data = await response.json();
                const result = data.result || data;
                const t = result.translations || {};
                const loadingHtml = `
                    <div class="alert alert-info simple-combo-alert recalculating" style="margin: 15px 0;">
                        <div style="text-align: center;">
                            <h4>🔄 ${this.getTranslation(t, 'recalculating', 'Recalculating combos...')}</h4>
                            <p>${this.getTranslation(t, 'cleaning_discounts', 'Clearing discounts and optimizing available packs')}</p>
                        </div>
                    </div>`;
                $('.oe_cart').before(loadingHtml);
                if (result.refresh) {
                    window.location.reload();
                    return;
                }
            } catch {
                // Errors are not user-critical here
            } finally {
                $('.simple-combo-alert.recalculating').remove();
                setTimeout(() => this.checkForCombos(), 500);
            }
        },

        async checkForCombos() {
            $('.simple-combo-alert').remove();
            try {
                const response = await fetch('/shop/check_combos', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    body: JSON.stringify({}),
                });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const data = await response.json();
                const combos = data.result || data || [];
                if (combos.length) {
                    this.showComboAlerts(combos);
                }
            } catch {
                // Ignore errors silently
            }
        },

        showComboAlerts(combos) {
            combos.forEach(combo => {
                const t = combo.translations || {};
                const symbol = combo.currency_symbol || '€';
                const position = combo.currency_position || 'after';
                const packText = this.getTranslation(t, 'pack_available', 'Pack Available');
                const savingsText = this.getTranslation(t, 'savings', 'Savings');
                const timesText = this.getTranslation(t, 'times_available', 'times available');
                const fromText = this.getTranslation(t, 'from', 'From');
                const forText = this.getTranslation(t, 'for', 'for');
                const applyText = this.getTranslation(t, 'apply_discount', 'Apply Discount');
                const qtyText = combo.times_available > 1 ? ` (${combo.times_available}x ${timesText})` : '';
                const savings = this.formatCurrency(combo.savings, symbol, position);
                const individual = this.formatCurrency(combo.individual_total, symbol, position);
                const comboPrice = this.formatCurrency(combo.combo_price, symbol, position);

                const alertHtml = `
                    <div class="alert alert-success simple-combo-alert" style="margin: 15px 0; border: 2px solid #28a745;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="margin: 0; color: #155724;">🎁 ${packText} "${combo.name}"!${qtyText}</h4>
                                <p style="margin: 5px 0;">
                                    <strong>${savingsText}: ${savings}</strong><br>
                                    <small>${fromText} ${individual} ${forText} ${comboPrice}</small>
                                </p>
                            </div>
                            <div>
                                <button class="btn btn-success btn-lg" onclick="comboManager.applyDiscount(${combo.id}, '${combo.name}', ${combo.savings}, '${symbol}', '${position}', event)">💰 ${applyText}</button>
                            </div>
                        </div>
                    </div>`;
                $('.oe_cart').before(alertHtml);
            });
        },

        async applyDiscount(id, name, savings, symbol, position, ev) {
            const button = ev.target;
            button.innerHTML = '⏳ Applying...';
            button.disabled = true;
            try {
                const response = await fetch(`/shop/apply_discount/${id}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    body: JSON.stringify({}),
                });
                const data = await response.json();
                const result = data.result || data;
                const t = result.translations || {};
                if (result.success) {
                    const applied = this.getTranslation(t, 'discount_applied', 'Discount Applied!');
                    $('.simple-combo-alert').removeClass('alert-success').addClass('alert-info');
                    $('.simple-combo-alert h4').text(`✅ ${applied}`);
                    $('.simple-combo-alert p').text(`<strong>${result.message}</strong>`);
                    $('.simple-combo-alert button').remove();
                    setTimeout(() => location.reload(), 2000);
                } else {
                    $('.simple-combo-alert').removeClass('alert-success').addClass('alert-warning');
                    const warn = this.getTranslation(t, 'warning', 'Warning');
                    $('.simple-combo-alert h4').text(`⚠️ ${warn}`);
                    $('.simple-combo-alert p').text(`<strong>${result.error}</strong>`);
                    $('.simple-combo-alert button').remove();
                    setTimeout(() => $('.simple-combo-alert').fadeOut(), 5000);
                }
            } catch (error) {
                $('.simple-combo-alert').removeClass('alert-success').addClass('alert-danger');
                const connErr = this.getTranslation({}, 'connection_error', 'Connection Error');
                $('.simple-combo-alert h4').text(`❌ ${connErr}`);
                $('.simple-combo-alert p').text(`<strong>Error: ${error.message}</strong>`);
                $('.simple-combo-alert button').remove();
                setTimeout(() => $('.simple-combo-alert').fadeOut(), 5000);
            }
        },
    };

    ComboManager.init();
    window.comboManager = ComboManager;
    window.checkForCombos = (...args) => ComboManager.checkForCombos(...args);
    window.showComboAlerts = (...args) => ComboManager.showComboAlerts(...args);
    window.applySimpleDiscount = (...args) => ComboManager.applyDiscount(...args);
    window.getSimpleCsrfToken = () => ComboManager.getCsrfToken();
    window.initCartObserver = (...args) => ComboManager.initCartObserver(...args);
    window.formatCurrency = (...args) => ComboManager.formatCurrency(...args);
})();
