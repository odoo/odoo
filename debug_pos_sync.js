const { chromium } = require('playwright');

async function debugPosSyncIssue() {
    // Launch browser with devtools open
    const browser = await chromium.launch({ 
        headless: false,
        devtools: true,
        args: ['--start-maximized']
    });
    
    const context = await browser.newContext({
        viewport: null // Use full screen
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
        
        // Add debug listeners for sync events
        await page.addInitScript(() => {
            // Monitor order sync events
            window.debugOrderSync = true;
            window.syncEvents = [];
            
            // Hook into console to capture sync-related logs
            const originalConsole = console.log;
            console.log = function(...args) {
                if (args.some(arg => 
                    typeof arg === 'string' && 
                    (arg.includes('sync') || arg.includes('order') || arg.includes('save_to_server'))
                )) {
                    window.syncEvents.push({
                        timestamp: new Date().toISOString(),
                        type: 'console',
                        args: args
                    });
                }
                originalConsole.apply(console, args);
            };
        });
        
        // Inject debugging functions
        await page.evaluate(() => {
            window.debugPos = function() {
                const pos = odoo.__DEBUG__.services['pos.store'] || odoo.pos;
                if (!pos) {
                    console.log('❌ POS not found');
                    return;
                }
                
                console.log('🔍 POS Debug Info:');
                console.log('Orders in memory:', pos.orders?.length || 'unknown');
                console.log('Orders in DB:', pos.db?.get_orders()?.length || 'unknown');
                console.log('Syncing orders:', pos.syncingOrders ? Array.from(pos.syncingOrders) : 'unknown');
                console.log('Pending orders:', pos.db?.get_orders() || []);
                
                return {
                    orders: pos.orders,
                    dbOrders: pos.db?.get_orders(),
                    syncingOrders: pos.syncingOrders ? Array.from(pos.syncingOrders) : [],
                    pos: pos
                };
            };
            
            window.createTestOrder = function() {
                const pos = odoo.__DEBUG__.services['pos.store'] || odoo.pos;
                if (!pos) {
                    console.log('❌ POS not found');
                    return;
                }
                
                // Create a new order
                const order = pos.createNewOrder();
                console.log('📝 Created test order:', order.name);
                
                // Add a product (assuming there are products loaded)
                const products = pos.models['product.product']?.cache || pos.db?.product_by_id;
                if (products) {
                    const productIds = Object.keys(products);
                    if (productIds.length > 0) {
                        const product = products[productIds[0]];
                        order.add_product(product);
                        console.log('➕ Added product to order:', product.display_name);
                    }
                }
                
                return order;
            };
            
            window.testOrderSync = async function() {
                const pos = odoo.__DEBUG__.services['pos.store'] || odoo.pos;
                if (!pos) {
                    console.log('❌ POS not found');
                    return;
                }
                
                console.log('🧪 Testing order sync...');
                const initialOrders = pos.db?.get_orders()?.length || 0;
                console.log('Initial orders in DB:', initialOrders);
                
                // Create and sync an order
                const order = window.createTestOrder();
                
                // Pay the order to make it ready for sync
                const paymentMethod = pos.payment_methods?.[0] || pos.config?.payment_methods?.[0];
                if (paymentMethod) {
                    order.add_paymentline(paymentMethod);
                    order.paymentlines.at(0).set_amount(order.get_total_with_tax());
                    console.log('💰 Added payment to order');
                }
                
                try {
                    console.log('🔄 Attempting to sync order...');
                    const result = await pos.push_single_order(order);
                    console.log('✅ Sync result:', result);
                    
                    const finalOrders = pos.db?.get_orders()?.length || 0;
                    console.log('Final orders in DB:', finalOrders);
                    console.log('Orders difference:', finalOrders - initialOrders);
                    
                    return result;
                } catch (error) {
                    console.log('❌ Sync failed:', error);
                    const finalOrders = pos.db?.get_orders()?.length || 0;
                    console.log('Final orders in DB after error:', finalOrders);
                    return error;
                }
            };
        });
        
        // Wait a bit for POS to fully initialize
        await page.waitForTimeout(5000);
        
        console.log('🔧 Injecting debug tools...');
        console.log('Available debug functions:');
        console.log('- window.debugPos() - Get POS state info');
        console.log('- window.createTestOrder() - Create a test order');
        console.log('- window.testOrderSync() - Test order synchronization');
        
        // Get initial state
        const initialState = await page.evaluate(() => window.debugPos());
        console.log('📊 Initial POS State:', initialState);
        
        console.log('\n🎯 Ready for debugging!');
        console.log('Browser DevTools are open. You can:');
        console.log('1. Use the injected debug functions in the console');
        console.log('2. Manually create orders and observe sync behavior');
        console.log('3. Check Network tab for API calls');
        console.log('4. Use Application tab to inspect local storage/IndexedDB');
        
        // Keep the browser open for manual debugging
        console.log('\n⏸️  Browser will stay open for manual debugging...');
        console.log('Press Ctrl+C to close when done.');
        
        // Wait indefinitely until manually closed
        await new Promise(() => {});
        
    } catch (error) {
        console.error('❌ Error during debugging:', error);
    } finally {
        await browser.close();
    }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n👋 Shutting down...');
    process.exit(0);
});

// Run the debug session
debugPosSyncIssue().catch(console.error);