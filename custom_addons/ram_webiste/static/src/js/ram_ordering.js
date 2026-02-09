// RAM Ordering System - Self-Executing Script
// Using Odoo 19 JSON2 API (jsonrpc is deprecated)
(function() {
    'use strict';
    
    // Odoo 19 JSON API call function (type="json" routes expect params in body)
    const callOdooAPI = async (route, params = {}) => {
        console.log("🌐 API Call:", route, "Params:", params);
        const response = await fetch(route, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Date.now(),
            }),
        });
        const data = await response.json();
        console.log("📥 API Response:", data);
        if (data.error) {
            console.error("API Error:", data.error);
            throw new Error(data.error.message || data.error.data?.message || 'API Error');
        }
        return data.result || data;
    };

    const RamOrdering = {
    cart: [],
    currentConfig: null,
    currentScreen: 'items', // 'items', 'checkout', 'success'

    formatPrice(amount) {
        const symbol = window.ram_currency_symbol || "Rs";
        const position = window.ram_currency_position || "before";
        const val = parseFloat(amount).toFixed(2);
        return position === "before" ? `${symbol}${val}` : `${val}${symbol}`;
    },

    async init() {
        console.log("🚀 RAM Ordering Engine V2 Initialized");
        
        // 1. Initial Load from LocalStorage
        this.loadCart();
        
        // 2. If logged in, sync with database
        if (window.ram_user_id) {
            console.log("🔄 User logged in, syncing cart with database...");
            try {
                // Ensure profile details are fetched sequentially
                await this.syncWithDatabase();
                await this.fetchProfileDetails();
            } catch (e) {
                console.error("Initialization sync failed (likely session or auth issue):", e);
                // Clear any infinite loader if it exists by allowing UI to update
            }
        }
        
        this.loadOrderHistory();
        this.bindEvents();
        this.updateUI();
        console.log("✅ RAM Ordering Engine initialization complete");
    },

    async fetchProfileDetails() {
        if (!window.ram_user_id) return;
        try {
            console.log("👤 Fetching profile for user:", window.ram_user_id);
            const profile = await callOdooAPI("/ram/user/profile");
            if (profile && !profile.error) {
                // Populate fields if they exist
                if (document.getElementById('ram_order_name')) document.getElementById('ram_order_name').value = profile.name || '';
                if (document.getElementById('ram_order_phone')) document.getElementById('ram_order_phone').value = profile.phone || '';
                if (document.getElementById('ram_order_email')) document.getElementById('ram_order_email').value = profile.email || '';
                
                // New Address Fields
                if (document.getElementById('ram_order_street')) document.getElementById('ram_order_street').value = profile.street || '';
                if (document.getElementById('ram_order_city')) document.getElementById('ram_order_city').value = profile.city || '';
                if (document.getElementById('ram_order_zip')) document.getElementById('ram_order_zip').value = profile.zip || '';
            }
        } catch (e) {
            console.error("Profile fetch failed:", e);
        }
    },

    bindEvents() {
        console.log("🎯 Binding click events...");
        document.addEventListener("click", async (e) => {
            // 1. Product Logic & Configurator Trigger
            const addToCartBtn = e.target.closest(".js_ram_add_to_cart");
            const dishTrigger = e.target.closest(".js_ram_dish_trigger");
            
            if (addToCartBtn) {
                e.preventDefault();
                e.stopPropagation();
                const productId = parseInt(addToCartBtn.dataset.productId);
                console.log(`🛒 Add to Cart clicked! Opening Configurator for: ${productId}`);
                this.openConfigurator(productId);
                return;
            } 
            
            if (dishTrigger) {
                // Card click also opens configurator
                e.preventDefault();
                e.stopPropagation();
                const productId = parseInt(dishTrigger.dataset.productId);
                console.log(`🎴 Card clicked! Opening Configurator for: ${productId}`);
                this.openConfigurator(productId);
                return;
            }

            // 2. Cart Toggle
            if (e.target.closest(".ram-cart-floating__btn") || e.target.closest(".js_ram_close_cart")) {
                this.toggleCart();
                return;
            }

            // Click outside sidebar to close
            const sidebar = document.getElementById("ram_cart_sidebar");
            if (sidebar && sidebar.classList.contains("active") && !e.target.closest(".ram-cart-sidebar") && !e.target.closest(".ram-cart-floating__btn")) {
                this.toggleCart(false);
            }

            // 3. Screen Navigation
            if (e.target.id === "js_ram_go_to_checkout") this.switchScreen('checkout');
            if (e.target.classList.contains("js_ram_back_to_cart")) this.switchScreen('items');
            
            // Tab Switching (Cart vs History)
            const tabBtn = e.target.closest(".js_ram_switch_tab");
            if (tabBtn) {
                const tab = tabBtn.dataset.tab;
                document.querySelectorAll(".js_ram_switch_tab").forEach(b => {
                    b.classList.toggle("active", b === tabBtn);
                });
                this.switchScreen(tab);
                if (tab === 'history') this.renderOrderHistory();
            }

            // 4. Cart Actions
            if (e.target.classList.contains("js_ram_remove_item")) this.removeItem(parseInt(e.target.dataset.index));
            if (e.target.classList.contains("js_ram_cart_plus")) this.updateItemQty(parseInt(e.target.dataset.index), 1);
            if (e.target.classList.contains("js_ram_cart_minus")) this.updateItemQty(parseInt(e.target.dataset.index), -1);

            // 5. Configurator Modal Logic
            if (e.target.closest(".js_ram_close_config")) this.toggleConfigModal(false);
            
            if (e.target.classList.contains("js_ram_config_select")) {
                const groupIdx = parseInt(e.target.dataset.groupIdx);
                const optionId = parseInt(e.target.dataset.optionId);
                const type = e.target.dataset.type;
                this.selectConfigOption(groupIdx, optionId, type);
            }

            if (e.target.id === "js_ram_add_configured_item") this.addConfiguredToCart();

            // 7. Final Submission
            if (e.target.id === "js_ram_submit_order") this.submitOrder();
        });

        // 8. One-time Closed Notification on Scroll
        if (!document.querySelector('.js_ram_add_to_cart:not([disabled])')) {
            let notified = false;
            window.addEventListener('scroll', () => {
                const menu = document.getElementById('menu');
                if (menu && !notified) {
                    const rect = menu.getBoundingClientRect();
                    if (rect.top < window.innerHeight && rect.bottom > 0) {
                        this.showToast("Restaurant is currently closed for remote orders.");
                        notified = true;
                    }
                }
            }, { passive: true });
        }
    },

    // --- Core Cart Logic ---

    addToCart(item) {
        // Simple deduplication only for items with NO variations
        if (!item.attribute_value_ids && !item.combo_line_ids) {
            const existing = this.cart.find(i => i.product_id === item.product_id && !i.attribute_value_ids);
            if (existing) {
                existing.qty += 1;
                this.saveCart();
                this.updateUI();
                this.showToast(`Updated ${item.name}`);
                return;
            }
        }

        this.cart.push(item);
        this.saveCart();
        this.updateUI();
        this.showToast(`Added ${item.name}`);

        if (this.cart.length === 1) this.toggleCart(true);
    },

    updateItemQty(index, delta) {
        const item = this.cart[index];
        if (!item) return;
        item.qty += delta;
        if (item.qty <= 0) {
            this.removeItem(index);
        } else {
            this.saveCart();
            this.updateUI();
        }
    },

    removeItem(index) {
        this.cart.splice(index, 1);
        this.saveCart();
        this.updateUI();
    },

    saveCart() { 
        localStorage.setItem("ram_cart_v2", JSON.stringify(this.cart)); 
        if (window.ram_user_id) {
            this.syncWithDatabase(true); // Background sync
        }
    },

    async syncWithDatabase(pushOnly = false) {
        if (!window.ram_user_id) return;
        
        try {
            if (pushOnly) {
                // Just push local cart to database
                await callOdooAPI("/ram/cart/sync", { cart_data: this.cart });
            } else {
                // Fetch from database and merge
                const result = await callOdooAPI("/ram/cart/get");
                if (result && result.cart) {
                    if (this.cart.length === 0) {
                        this.cart = result.cart;
                        localStorage.setItem("ram_cart_v2", JSON.stringify(this.cart));
                        this.updateUI();
                    } else {
                        await callOdooAPI("/ram/cart/sync", { cart_data: this.cart });
                    }
                }
            }
        } catch (e) {
            console.error("Cart sync failed:", e);
        } finally {
            // Ensure any loading state is cleared
            // If we have a general page loader, hide it here
        }
    },
    loadCart() {
        const saved = localStorage.getItem("ram_cart_v2");
        if (saved) {
            try { this.cart = JSON.parse(saved); } catch (e) { this.cart = []; }
        }
    },

    saveCustomerDetails(details) {
        localStorage.setItem("ram_customer_details", JSON.stringify(details));
    },

    loadCustomerDetails() {
        const saved = localStorage.getItem("ram_customer_details");
        if (saved) {
            try {
                const details = JSON.parse(saved);
                const fields = {
                    'ram_order_name': details.name,
                    'ram_order_phone': details.phone,
                    'ram_order_email': details.email,
                    'ram_order_address': details.address
                };
                Object.entries(fields).forEach(([id, val]) => {
                    const el = document.getElementById(id);
                    if (el && val) el.value = val;
                });
            } catch (e) { console.error("History load error", e); }
        }
    },

    saveOrderHistory(order) {
        let history = this.getOrderHistory();
        history.unshift({
            ref: order.pos_reference,
            date: new Date().toLocaleString(),
            total: this.cart.reduce((sum, i) => sum + (i.price * i.qty), 0).toFixed(2),
            status: order.status || 'received'
        });
        localStorage.setItem("ram_order_history", JSON.stringify(history.slice(0, 10))); // Keep last 10
    },

    getOrderHistory() {
        const saved = localStorage.getItem("ram_order_history");
        try { return saved ? JSON.parse(saved) : []; } catch (e) { return []; }
    },

    loadOrderHistory() {
        this.renderOrderHistory();
    },

    renderOrderHistory() {
        const container = document.getElementById("ram_order_history_list");
        if (!container) return;
        const history = this.getOrderHistory();
        if (history.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-muted">No recent orders found</div>';
            return;
        }
        container.innerHTML = history.map(h => {
            // Priority 1: Direct Invoice URL with token (from recent submission)
            // Priority 2: Standard Invoice Path (fallback for older history)
            const targetUrl = h.invoice_url || (h.invoice_id ? `/my/invoices/${h.invoice_id}` : '/my/invoices');
            
            return `
            <div class="ram-history-item p-3 mb-2 border rounded border-secondary" style="cursor: pointer;" 
                 onclick="window.location.href='${targetUrl}'">
                <div class="d-flex justify-content-between">
                    <strong class="text-primary">${h.pos_reference || h.ref}</strong>
                    <span class="badge bg-primary">${h.status || h.state}</span>
                </div>
                <div class="small text-muted mt-1">${h.date} • ${this.formatPrice(h.amount_total || h.total)}</div>
            </div>
        `}).join("");
    },

    // --- Configurator Logic ---

    async openConfigurator(productId) {
        this.toggleConfigModal(true, true); // show loader
        try {
            const data = await callOdooAPI("/ram/product/details", { product_id: productId });
            if (data.error) throw new Error(data.error);

            this.currentConfig = {
                product_id: data.id,
                name: data.name,
                base_price: data.list_price,
                tax_amount: data.tax_amount || 0,
                thumb: data.image_url,
                attributes: data.attributes || [],
                combos: data.combos || [],
                selections: {
                    attributes: {}, // { attr_id: value_id }
                    combos: {}     // { combo_id: item_id }
                }
            };

            // Pre-select defaults
            this.currentConfig.attributes.forEach(attr => {
                if (attr.values.length > 0) this.currentConfig.selections.attributes[attr.id] = attr.values[0].id;
            });
            this.currentConfig.combos.forEach(combo => {
                if (combo.items.length > 0) this.currentConfig.selections.combos[combo.id] = combo.items[0].id;
            });

            this.renderConfigurator();
        } catch (e) {
            alert("Failed to load product details: " + e.message);
            this.toggleConfigModal(false);
        }
    },


    renderConfigurator() {
        const body = document.getElementById("ram_config_body");
        const title = document.getElementById("ram_config_title");
        if (!body || !this.currentConfig) return;

        title.textContent = this.currentConfig.name;

        let html = '';

        // Attributes (e.g., Spice Level)
        this.currentConfig.attributes.forEach((attr, idx) => {
            html += `
                <div class="ram-config-group">
                    <div class="ram-config-group__title">${attr.name}</div>
                    <div class="ram-config-options">
                        ${attr.values.map(val => `
                            <div class="ram-config-option js_ram_config_select ${this.currentConfig.selections.attributes[attr.id] === val.id ? 'active' : ''}" 
                                 data-group-idx="${attr.id}" data-option-id="${val.id}" data-type="attribute">
                                <span class="ram-config-option__name">${val.name}</span>
                                ${val.price_extra > 0 ? `<span class="ram-config-option__price">+${this.formatPrice(val.price_extra)}</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        // Combos (e.g., Choose your Drink)
        this.currentConfig.combos.forEach((combo, idx) => {
            html += `
                <div class="ram-config-group">
                    <div class="ram-config-group__title">${combo.name}</div>
                    <div class="ram-config-options">
                        ${combo.items.map(item => `
                            <div class="ram-config-option js_ram_config_select ${this.currentConfig.selections.combos[combo.id] === item.id ? 'active' : ''}" 
                                 data-group-idx="${combo.id}" data-option-id="${item.id}" data-type="combo">
                                <img src="${item.image}" class="ram-config-option__img" />
                                <span class="ram-config-option__name">${item.name}</span>
                                ${item.price_extra > 0 ? `<span class="ram-config-option__price">+${this.formatPrice(item.price_extra)}</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        // Add Note Field
        html += `
            <div class="ram-config-group">
                <div class="ram-config-group__title">Special Instructions</div>
                <textarea id="ram_config_note" class="form-control" rows="2" placeholder="Ex: No ice, extra spicy..."></textarea>
            </div>
        `;

        body.innerHTML = html;
        this.calculateConfigPrice();
    },
    selectConfigOption(groupId, optionId, type) {
        if (type === 'attribute') this.currentConfig.selections.attributes[groupId] = optionId;
        else this.currentConfig.selections.combos[groupId] = optionId;
        this.renderConfigurator();
    },

    calculateConfigPrice() {
        let total = this.currentConfig.base_price;
        
        Object.entries(this.currentConfig.selections.attributes).forEach(([attrId, valId]) => {
            const attr = this.currentConfig.attributes.find(a => a.id == attrId);
            if (attr) {
                const val = attr.values.find(v => v.id == valId);
                if (val) total += val.price_extra;
            }
        });

        Object.entries(this.currentConfig.selections.combos).forEach(([comboId, itemId]) => {
            const combo = this.currentConfig.combos.find(c => c.id == comboId);
            if (combo) {
                const item = combo.items.find(i => i.id == itemId);
                if (item) total += item.price_extra;
            }
        });

        const target = document.getElementById("ram_config_total_price");
        if (target) {
            target.textContent = total.toFixed(2);
            // Also update the visible parent label if it exists
            const parent = target.parentElement;
            if (parent && parent.innerText.includes('Total')) {
                // Ensure currency symbol is preserved or re-added if we want full replacement
                // For now, fast fix: just update the number
            }
        }
    },
    
    _getCalculatedConfigTotal() {
        // Fallback helper for submission
        let total = this.currentConfig.base_price;
        Object.entries(this.currentConfig.selections.attributes).forEach(([attrId, valId]) => {
            const attr = this.currentConfig.attributes.find(a => a.id == attrId);
            if (attr) {
                const val = attr.values.find(v => v.id == valId);
                if (val) total += val.price_extra;
            }
        });
        Object.entries(this.currentConfig.selections.combos).forEach(([comboId, itemId]) => {
            const combo = this.currentConfig.combos.find(c => c.id == comboId);
            if (combo) {
                const item = combo.items.find(i => i.id == itemId);
                if (item) total += item.price_extra;
            }
        });
        return total;
    },

    addConfiguredToCart() {
        const selections = this.currentConfig.selections;
        let summary = [];
        
        const attribute_value_ids = Object.values(selections.attributes);
        const combo_line_ids = Object.entries(selections.combos).map(([comboId, itemId]) => {
            const combo = this.currentConfig.combos.find(c => c.id == comboId);
            const item = combo.items.find(i => i.id == itemId);
            summary.push(item.name);
            return { combo_id: parseInt(comboId), combo_item_id: parseInt(itemId), product_id: item.product_id, qty: 1 };
        });

        // Add attribute names to summary
        Object.entries(selections.attributes).forEach(([attrId, valId]) => {
            const attr = this.currentConfig.attributes.find(a => a.id == attrId);
            const val = attr.values.find(v => v.id == valId);
            summary.push(val.name);
        });

        // Capture the note from the modal
        const note = document.getElementById('ram_config_note')?.value || '';

        this.addToCart({
            product_id: this.currentConfig.product_id,
            name: this.currentConfig.name,
            price: parseFloat(document.getElementById("ram_config_total_price").text), // Accessing .textContent was fine, but let's check parse
            price: parseFloat(document.getElementById("ram_config_total_price").textContent), 
            tax_amount: this.currentConfig.tax_amount, 
            qty: 1,
            thumb: this.currentConfig.thumb,
            variation_summary: summary.join(", "),
            attribute_value_ids: attribute_value_ids,
            combo_line_ids: combo_line_ids,
            note: note
        });

        this.toggleConfigModal(false);
    },

    // --- UI State Helpers ---

    toggleCart(forceOpen) {
        const sidebar = document.getElementById("ram_cart_sidebar");
        if (!sidebar) return;
        const isOpen = sidebar.classList.contains("active");
        const newState = forceOpen !== undefined ? forceOpen : !isOpen;
        sidebar.classList.toggle("active", newState);
        sidebar.setAttribute("aria-hidden", (!newState).toString());
    },

    toggleConfigModal(show, loading = false) {
        console.log("🎭 toggleConfigModal called:", { show, loading });
        const modal = document.getElementById("ram_config_modal");
        console.log("📦 Modal element:", modal);
        if (!modal) {
            console.error("❌ Modal element 'ram_config_modal' not found in DOM!");
            return;
        }
        modal.classList.toggle("active", show);
        console.log("✅ Modal classes after toggle:", modal.classList.toString());
        if (loading) {
            document.getElementById("ram_config_body").innerHTML = '<div class="text-center py-5"><i class="fa fa-spinner fa-spin fa-2x"></i></div>';
            document.getElementById("ram_config_title").textContent = "Loading...";
        }
    },

    async switchScreen(screenName) {
        if (screenName === 'checkout' && !window.ram_user_id) {
            this.showToast("Please login/signup to continue.");
            setTimeout(() => {
                window.location.href = "/web/login?redirect=" + encodeURIComponent(window.location.pathname);
            }, 1000);
            return;
        }
        this.currentScreen = screenName;
        document.querySelectorAll(".ram-cart-screen").forEach(s => s.classList.add("d-none"));
        const target = document.getElementById(`ram_cart_screen_${screenName}`);
        if (target) target.classList.remove("d-none");
    },

    updateUI() {
        const totalItems = this.cart.reduce((sum, i) => sum + i.qty, 0);
        const totalPrice = this.cart.reduce((sum, i) => sum + (i.price * i.qty), 0);
        const totalTax = this.cart.reduce((sum, i) => sum + ((i.tax_amount || 0) * i.qty), 0);

        document.querySelectorAll(".ram-cart-count").forEach(el => el.textContent = totalItems);
        document.querySelectorAll(".ram-cart-total-price").forEach(el => el.textContent = totalPrice.toFixed(2));
        document.querySelectorAll(".ram-cart-total-tax").forEach(el => el.textContent = totalTax.toFixed(2));

        const floating = document.getElementById("ram_cart_floating");
        if (floating) {
            floating.classList.toggle("d-none", totalItems === 0);
        }

        const itemsContainer = document.getElementById("ram_cart_items");
        if (!itemsContainer) return;

        if (this.cart.length === 0) {
            itemsContainer.innerHTML = '<div class="ram-empty-cart">No items in cart</div>';
            const checkoutBtn = document.getElementById("js_ram_go_to_checkout");
            if (checkoutBtn) checkoutBtn.classList.add("d-none");
        } else {
            itemsContainer.innerHTML = this.cart.map((item, idx) => `
                <div class="ram-cart-item">
                    <div class="ram-cart-item__thumb-wrapper">
                        <img src="${item.thumb || '/web/static/img/placeholder.png'}" class="ram-cart-item__thumb" loading="lazy" />
                    </div>
                    <div class="ram-cart-item__info">
                        <div class="ram-cart-item__name">${item.name}</div>
                        <div class="ram-cart-item__controls">
                            <button class="ram-cart-qty-btn js_ram_cart_minus" data-index="${idx}">-</button>
                            <span class="ram-cart-qty-val">${item.qty}</span>
                            <button class="ram-cart-qty-btn js_ram_cart_plus" data-index="${idx}">+</button>
                        </div>
                        ${item.variation_summary ? `<div class="small text-muted">${item.variation_summary}</div>` : ''}
                    </div>
                    <div class="text-end">
                        <div class="fw-bold">${this.formatPrice(item.price * item.qty)}</div>
                        <button class="btn btn-sm text-danger js_ram_remove_item mt-2" data-index="${idx}">Remove</button>
                    </div>
                </div>
            `).join("");
            const checkoutBtn = document.getElementById("js_ram_go_to_checkout");
            if (checkoutBtn) checkoutBtn.classList.remove("d-none");
        }
    },

    async submitOrder() {
        const name = document.getElementById("ram_order_name").value.trim();
        const phone = document.getElementById("ram_order_phone").value.trim();
        const email = document.getElementById("ram_order_email").value.trim();
        const address = ""; // Unused now
        const street = document.getElementById("ram_order_street").value.trim();
        const city = document.getElementById("ram_order_city").value.trim();
        
        // Get selected payment method
        const paymentMethod = document.querySelector('input[name="ram_payment"]:checked');
        const paymentValue = paymentMethod ? paymentMethod.value : 'counter';
        
        console.log("💳 Payment method selected:", paymentValue);

        if (!name || !phone || !email) {
            alert("Name, Phone, and Email are required.");
            return;
        }

        // Validate Card Details if Online
        if (paymentValue === 'online') {
            const cardNum = document.querySelector('#ram_card_form input[placeholder*="XXXX"]').value.replace(/\s/g, '');
            const cardExpiry = document.querySelector('#ram_card_form input[placeholder="MM/YY"]').value.trim();
            
            if (cardNum.length < 13) {
                alert("Please enter a valid card number.");
                return;
            }
            
            // Regex for MM/YY
            const expiryRegex = /^(0[1-9]|1[0-2])\/([0-9]{2})$/;
            if (!expiryRegex.test(cardExpiry)) {
                alert("Please enter a valid expiry date in MM/YY format (e.g. 12/25).");
                return;
            }
        }

        const btn = document.getElementById("js_ram_submit_order");
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Processing...';

        const orderData = {
            lines: this.cart,
            customer_name: name,
            customer_phone: phone,
            customer_email: email,
            // Split Address
            customer_street: document.getElementById("ram_order_street").value.trim(),
            customer_city: document.getElementById("ram_order_city").value.trim(),
            customer_zip: document.getElementById("ram_order_zip").value.trim(),
            notes: document.getElementById('ram_order_notes')?.value || '',
            payment_method: paymentValue, 
        };

        /**
         * PRODUCTION PLAN: Payment Integration
         * 
         * Currently, 'online' payment is mocked using the POS session's 'Online' payment method.
         * For production:
         * 1. Integrate a backend route for payment intent creation (Stripe/Razorpay).
         * 2. Use the payment gateway's JS SDK here to collect payment details.
         * 3. Only call /ram/order/submit AFTER successful payment confirmation from the gateway.
         * 4. Pass the payment transaction ID/reference to Odoo for reconciliation.
         * 5. 'Pay at Counter' should likely be disabled or restricted in production for pure online ordering.
         */

        try {
            const result = await callOdooAPI("/ram/order/submit", { order_data: orderData });
            if (result.error) {
                alert("Order Failed: " + result.error);
            } else {
                // No more local storage of PII
                this.saveOrderHistory(result);
                this.cart = [];
                this.saveCart();
                this.updateUI();
                this.renderOrderHistory();
                document.getElementById("ram_success_ref").textContent = result.pos_reference;
                this.switchScreen('success');
            }
        } catch (e) {
            alert("Network error. Please try again.");
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    },

    showToast(msg) {
        console.log("RAM Toast:", msg);
        // Could be expanded to a real floating toast
    }
};

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => RamOrdering.init());

})(); // Close the IIFE
