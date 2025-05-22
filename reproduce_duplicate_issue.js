const { chromium } = require('playwright');

async function reproduceDuplicateIssue() {
    const browser = await chromium.launch({ 
        headless: false,
        devtools: true,
        args: ['--start-maximized']
    });
    
    const context = await browser.newContext({
        viewport: null
    });
    
    const page = await context.newPage();
    
    try {
        console.log('🚀 Navigating to Odoo POS...');
        await page.goto('https://80914671-16-0-all.runbot169.odoo.com/pos/ui?config_id=1#cids=1');
        
        // Wait for login form and login
        console.log('🔐 Logging in...');
        await page.waitForSelector('input[name="login"]', { timeout: 30000 });
        await page.fill('input[name="login"]', 'admin');
        await page.fill('input[name="password"]', 'admin');
        await page.click('button[type="submit"]');
        
        // Wait for POS to load
        console.log('⏳ Waiting for POS interface...');
        await page.waitForSelector('.pos-content, .product-screen, .pos', { timeout: 60000 });
        
        // Wait a bit more for full initialization
        await page.waitForTimeout(5000);
        
        console.log('✅ POS loaded! Setting up debugging hooks...');
        
        // Inject comprehensive debugging
        await page.evaluate(() => {
            window.syncEvents = [];
            window.orderStates = [];
            
            // Function to capture order state
            window.captureOrderState = function(label) {
                const pos = odoo?.pos || window.pos;
                if (!pos) return;
                
                const state = {
                    timestamp: new Date().toISOString(),
                    label: label,
                    dbOrders: pos.db?.get_orders()?.length || 0,
                    dbOrderDetails: pos.db?.get_orders()?.map(o => ({
                        id: o.id,
                        name: o.name,
                        state: o.state,
                        server_id: o.server_id
                    })) || [],
                    syncingOrders: pos.syncingOrders ? Array.from(pos.syncingOrders) : [],
                    currentOrderName: pos.get_order()?.name || 'none'
                };
                
                window.orderStates.push(state);
                console.log(`📊 [${label}]`, state);
                return state;
            };
            
            // Hook into critical methods once POS is ready
            const hookPosMethodsWhenReady = () => {
                const pos = odoo?.pos || window.pos;
                if (!pos) {
                    setTimeout(hookPosMethodsWhenReady, 500);
                    return;
                }
                
                console.log('🎯 Hooking into POS methods...');
                
                // Hook _save_to_server
                if (pos._save_to_server && !pos._save_to_server._hooked) {
                    const original_save_to_server = pos._save_to_server;
                    pos._save_to_server = function(orders, options) {
                        console.log('🔄 _save_to_server called with orders:', orders.map(o => `${o.name} (${o.id})`));
                        window.captureOrderState('Before _save_to_server');
                        
                        return original_save_to_server.call(this, orders, options)
                            .then(result => {
                                console.log('✅ _save_to_server SUCCESS:', result);
                                window.captureOrderState('After _save_to_server SUCCESS');
                                return result;
                            })
                            .catch(error => {
                                console.log('❌ _save_to_server ERROR:', error);
                                window.captureOrderState('After _save_to_server ERROR');
                                throw error;
                            });
                    };
                    pos._save_to_server._hooked = true;
                }
                
                // Hook db.remove_order
                if (pos.db?.remove_order && !pos.db.remove_order._hooked) {
                    const original_remove_order = pos.db.remove_order;
                    pos.db.remove_order = function(order_id) {
                        console.log('🗑️ DB: Removing order:', order_id);
                        console.trace('Remove order call stack');
                        return original_remove_order.call(this, order_id);
                    };
                    pos.db.remove_order._hooked = true;
                }
                
                // Hook push_single_order
                if (pos.push_single_order && !pos.push_single_order._hooked) {
                    const original_push_single_order = pos.push_single_order;
                    pos.push_single_order = function(order, opts) {
                        console.log('📤 push_single_order called for:', order.name);
                        window.captureOrderState('Before push_single_order');
                        
                        return original_push_single_order.call(this, order, opts)
                            .then(result => {
                                console.log('✅ push_single_order SUCCESS:', result);
                                window.captureOrderState('After push_single_order SUCCESS');
                                return result;
                            })
                            .catch(error => {
                                console.log('❌ push_single_order ERROR:', error);
                                window.captureOrderState('After push_single_order ERROR');
                                throw error;
                            });
                    };
                    pos.push_single_order._hooked = true;
                }
            };
            
            hookPosMethodsWhenReady();
        });
        
        console.log('🎯 Starting reproduction steps...');
        
        // Step 1: Add items to cart
        console.log('📦 Step 1: Adding items to cart...');
        await page.evaluate(() => window.captureOrderState('Initial state'));
        
        // Wait for products to load and click the first available product
        await page.waitForSelector('.product', { timeout: 10000 });
        const products = await page.$$('.product');
        if (products.length > 0) {
            await products[0].click();
            console.log('✅ Added first product to cart');
            await page.waitForTimeout(1000);
        }
        
        await page.evaluate(() => window.captureOrderState('After adding product'));
        
        // Step 2: Click payment button
        console.log('💳 Step 2: Clicking payment button...');
        await page.waitForSelector('.pay-circle, .button.pay, [data-hotkey="3"], .pay-button', { timeout: 10000 });
        
        // Try multiple possible selectors for the payment button
        const paymentClicked = await page.evaluate(() => {
            // Try various selectors for the payment button
            const selectors = [
                '.pay-circle',
                '.button.pay', 
                '[data-hotkey="3"]',
                '.pay-button',
                '.payment-button',
                'button:has-text("Payment")',
                'div:has-text("Payment")'
            ];
            
            for (const selector of selectors) {
                const elem = document.querySelector(selector);
                if (elem && elem.offsetParent !== null) { // visible element
                    elem.click();
                    console.log('✅ Clicked payment button with selector:', selector);
                    return true;
                }
            }
            return false;
        });
        
        if (!paymentClicked) {
            // Alternative: look for any button with payment-related text
            await page.click('text=/payment/i');
        }
        
        await page.waitForTimeout(2000);
        await page.evaluate(() => window.captureOrderState('After clicking payment'));
        
        // Step 3: Select cash payment method
        console.log('💰 Step 3: Selecting cash payment method...');
        await page.waitForSelector('.paymentmethod, .payment-method, [data-payment-method]', { timeout: 10000 });
        
        // Click on cash payment method (usually the first one)
        const cashClicked = await page.evaluate(() => {
            const cashSelectors = [
                '.paymentmethod:first-child',
                '.payment-method:first-child',
                '[data-payment-method]:first-child',
                'div:has-text("Cash")',
                'button:has-text("Cash")'
            ];
            
            for (const selector of selectors) {
                const elem = document.querySelector(selector);
                if (elem && elem.offsetParent !== null) {
                    elem.click();
                    console.log('✅ Selected cash payment method');
                    return true;
                }
            }
            return false;
        });
        
        if (!cashClicked) {
            await page.click('.paymentmethod, .payment-method, [data-payment-method]');
        }
        
        await page.waitForTimeout(1000);
        await page.evaluate(() => window.captureOrderState('After selecting cash'));
        
        // Step 4: Click validate button
        console.log('✔️ Step 4: Clicking validate button...');
        await page.waitForSelector('.next, .validate, .confirm, button:has-text("Validate")', { timeout: 10000 });
        
        const validateClicked = await page.evaluate(() => {
            const validateSelectors = [
                '.next',
                '.validate', 
                '.confirm',
                'button:has-text("Validate")',
                'div:has-text("Validate")',
                '.button.next'
            ];
            
            for (const selector of validateSelectors) {
                const elem = document.querySelector(selector);
                if (elem && elem.offsetParent !== null) {
                    elem.click();
                    console.log('✅ Clicked validate button');
                    return true;
                }
            }
            return false;
        });
        
        if (!validateClicked) {
            await page.click('text=/validate/i');
        }
        
        await page.waitForTimeout(3000);
        await page.evaluate(() => window.captureOrderState('After validate - immediate'));
        
        // Wait a bit more for sync to complete
        await page.waitForTimeout(5000);
        await page.evaluate(() => window.captureOrderState('After validate - delayed'));
        
        // Analysis
        console.log('\n🔍 === ANALYSIS ===');
        const finalAnalysis = await page.evaluate(() => {
            console.log('\n📊 === ORDER STATE TIMELINE ===');
            window.orderStates.forEach((state, i) => {
                console.log(`${i+1}. [${state.label}] DB Orders: ${state.dbOrders}, Syncing: [${state.syncingOrders.join(', ')}]`);
                if (state.dbOrderDetails.length > 0) {
                    state.dbOrderDetails.forEach(order => {
                        console.log(`   - ${order.name} (ID: ${order.id}, State: ${order.state}, Server ID: ${order.server_id})`);
                    });
                }
            });
            
            const currentState = window.captureOrderState('Final analysis');
            return currentState;
        });
        
        console.log('\n🚨 === DUPLICATE ORDER ANALYSIS ===');
        if (finalAnalysis.dbOrders > 0) {
            console.log(`❌ ISSUE CONFIRMED: ${finalAnalysis.dbOrders} unsynced orders remaining in localStorage`);
            console.log('📋 Remaining orders:', finalAnalysis.dbOrderDetails);
            
            // Check if any orders have server_id but are still in local storage
            const problematicOrders = finalAnalysis.dbOrderDetails.filter(order => 
                order.server_id || order.state === 'paid' || order.state === 'done'
            );
            
            if (problematicOrders.length > 0) {
                console.log('🔥 CRITICAL: These orders appear to be synced but still in localStorage:');
                problematicOrders.forEach(order => console.log(`   - ${order.name} (Server ID: ${order.server_id}, State: ${order.state})`));
            }
        } else {
            console.log('✅ No duplicate orders found - fix appears to be working');
        }
        
        console.log('\n⏸️ Browser will remain open for manual inspection...');
        console.log('Check DevTools Console for detailed logs and use window.captureOrderState("manual check") for current state');
        
        // Keep browser open for manual inspection
        await page.waitForTimeout(300000); // 5 minutes
        
    } catch (error) {
        console.error('❌ Error during reproduction:', error);
    } finally {
        console.log('👋 Closing browser...');
        await browser.close();
    }
}

reproduceDuplicateIssue().catch(console.error);