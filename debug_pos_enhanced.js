const { chromium } = require('playwright');

async function debugPosSyncIssue() {
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
        
        // Wait for login form
        console.log('🔐 Waiting for login form...');
        await page.waitForSelector('input[name="login"]', { timeout: 30000 });
        
        // Login
        console.log('📝 Filling login credentials...');
        await page.fill('input[name="login"]', 'admin');
        await page.fill('input[name="password"]', 'admin');
        await page.click('button[type="submit"]');
        
        // Wait for POS to load
        console.log('⏳ Waiting for POS interface...');
        await page.waitForSelector('.pos-content, .product-screen, .pos', { timeout: 60000 });
        
        console.log('✅ POS loaded successfully!');
        
        // Enhanced debugging functions
        await page.evaluate(() => {
            // Store original methods to monitor them
            window.originalMethods = {};
            
            // Hook into the POS system after it loads
            const waitForPos = () => {
                const pos = odoo?.pos || window.pos;
                if (!pos) {
                    setTimeout(waitForPos, 1000);
                    return;
                }
                
                console.log('🎯 POS System found, hooking into methods...');
                
                // Hook into _save_to_server method to monitor sync behavior
                if (pos._save_to_server) {
                    window.originalMethods._save_to_server = pos._save_to_server;
                    pos._save_to_server = function(orders, options) {
                        console.log('🔄 _save_to_server called with orders:', orders.map(o => ({
                            id: o.id,
                            name: o.name || o.pos_reference,
                            state: o.state
                        })));
                        console.log('📊 Orders in DB before sync:', pos.db.get_orders().length);
                        
                        return window.originalMethods._save_to_server.call(this, orders, options)
                            .then(result => {
                                console.log('✅ _save_to_server result:', result);
                                console.log('📊 Orders in DB after sync:', pos.db.get_orders().length);
                                console.log('🔍 Remaining orders:', pos.db.get_orders().map(o => ({
                                    id: o.id,
                                    name: o.name,
                                    state: o.state
                                })));
                                return result;
                            })
                            .catch(error => {
                                console.log('❌ _save_to_server error:', error);
                                console.log('📊 Orders in DB after error:', pos.db.get_orders().length);
                                throw error;
                            });
                    };
                }
                
                // Hook into db.remove_order to see when orders are removed
                if (pos.db && pos.db.remove_order) {
                    window.originalMethods.remove_order = pos.db.remove_order;
                    pos.db.remove_order = function(order_id) {
                        console.log('🗑️ Removing order from DB:', order_id);
                        console.trace('Remove order call stack');
                        return window.originalMethods.remove_order.call(this, order_id);
                    };
                }
                
                // Monitor order creation
                if (pos.createNewOrder) {
                    window.originalMethods.createNewOrder = pos.createNewOrder;
                    pos.createNewOrder = function() {
                        const order = window.originalMethods.createNewOrder.call(this);
                        console.log('📝 New order created:', order.name, 'ID:', order.id);
                        return order;
                    };
                }
            };
            
            waitForPos();
            
            // Enhanced debug functions
            window.debugPos = function() {
                const pos = odoo?.pos || window.pos;
                if (!pos) {
                    console.log('❌ POS not found');
                    return null;
                }
                
                const dbOrders = pos.db?.get_orders() || [];
                const memoryOrders = pos.orders || [];
                
                console.log('🔍 === POS DEBUG INFO ===');
                console.log('Orders in memory:', memoryOrders.length);
                console.log('Orders in DB:', dbOrders.length);
                console.log('Syncing orders:', pos.syncingOrders ? Array.from(pos.syncingOrders) : []);
                
                console.log('\n📋 DB Orders:');
                dbOrders.forEach((order, i) => {
                    console.log(`  ${i+1}. ${order.name} (ID: ${order.id}, State: ${order.state})`);
                });
                
                console.log('\n🧠 Memory Orders:');
                memoryOrders.forEach((order, i) => {
                    console.log(`  ${i+1}. ${order.name} (ID: ${order.id}, State: ${order.state})`);
                });
                
                return {
                    memoryOrders: memoryOrders.length,
                    dbOrders: dbOrders.length,
                    syncingOrders: pos.syncingOrders ? Array.from(pos.syncingOrders) : [],
                    orders: dbOrders,
                    pos: pos
                };
            };
            
            window.simulateDuplicateIssue = async function() {
                const pos = odoo?.pos || window.pos;
                if (!pos) {
                    console.log('❌ POS not found');
                    return;
                }
                
                console.log('🧪 Simulating duplicate order issue...');
                
                // Create a test order
                const order = pos.createNewOrder();
                
                // Add a product if available
                const products = Object.values(pos.db?.product_by_id || {});
                if (products.length > 0) {
                    order.add_product(products[0]);
                    console.log('➕ Added product to order');
                }
                
                // Add payment
                const paymentMethods = pos.payment_methods || [];
                if (paymentMethods.length > 0) {
                    order.add_paymentline(paymentMethods[0]);
                    order.paymentlines.at(0).set_amount(order.get_total_with_tax());
                    console.log('💰 Added payment to order');
                }
                
                console.log('📊 State before sync:', window.debugPos());
                
                try {
                    // Attempt sync
                    console.log('🔄 Attempting to sync order...');
                    const result = await pos.push_single_order(order);
                    console.log('✅ Sync completed:', result);
                    
                    setTimeout(() => {
                        console.log('📊 State after sync (delayed check):', window.debugPos());
                    }, 2000);
                    
                } catch (error) {
                    console.log('❌ Sync failed:', error);
                    console.log('📊 State after error:', window.debugPos());
                }
            };
            
            window.inspectNetworkCalls = function() {
                // Monitor network calls related to POS
                const originalFetch = window.fetch;
                window.fetch = function(...args) {
                    const url = args[0];
                    if (url.includes('/web/dataset/call_kw') || url.includes('pos.order')) {
                        console.log('🌐 Network call:', url, args[1]?.body ? JSON.parse(args[1].body) : '');
                    }
                    return originalFetch.apply(this, args);
                };
                console.log('👁️ Network monitoring enabled');
            };
        });
        
        // Wait for POS to fully initialize
        await page.waitForTimeout(5000);
        
        // Run initial debug
        const state = await page.evaluate(() => window.debugPos());
        console.log('📊 Initial state:', state);
        
        // Enable network monitoring
        await page.evaluate(() => window.inspectNetworkCalls());
        
        console.log('\n🎯 === DEBUGGING COMMANDS ===');
        console.log('window.debugPos() - Check current POS state');
        console.log('window.simulateDuplicateIssue() - Simulate the duplicate order issue');
        console.log('window.inspectNetworkCalls() - Monitor network calls');
        
        console.log('\n🔍 === INVESTIGATION STEPS ===');
        console.log('1. Open DevTools Console (F12)');
        console.log('2. Run: window.simulateDuplicateIssue()');
        console.log('3. Watch for duplicate orders in the output');
        console.log('4. Check Network tab for failed/duplicate API calls');
        
        // Wait for manual interaction
        await page.waitForTimeout(300000); // 5 minutes timeout
        
    } catch (error) {
        console.error('❌ Error:', error);
    } finally {
        console.log('👋 Closing browser...');
        await browser.close();
    }
}

debugPosSyncIssue().catch(console.error);