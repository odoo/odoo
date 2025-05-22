const { chromium } = require('playwright');

async function simpleDebug() {
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
        console.log('🚀 Opening POS...');
        await page.goto('https://80914671-16-0-all.runbot169.odoo.com/pos/ui?config_id=1#cids=1');
        
        // Login
        await page.waitForSelector('input[name="login"]', { timeout: 30000 });
        await page.fill('input[name="login"]', 'admin');
        await page.fill('input[name="password"]', 'admin');
        await page.click('button[type="submit"]');
        
        // Wait for POS
        await page.waitForSelector('.pos-content, .product-screen, .pos', { timeout: 60000 });
        await page.waitForTimeout(3000);
        
        console.log('✅ POS loaded! Injecting debug tools...');
        
        // Inject simple but effective debugging
        await page.evaluate(() => {
            window.DEBUG_ENABLED = true;
            window.orderStates = [];
            
            const waitForPos = () => {
                const pos = odoo?.pos || window.pos;
                if (!pos) {
                    setTimeout(waitForPos, 500);
                    return;
                }
                
                console.log('🎯 POS found! Installing hooks...');
                
                // Simple state capture function
                window.captureState = function(label = 'manual') {
                    const dbOrders = pos.db?.get_orders() || [];
                    const state = {
                        label,
                        timestamp: new Date().toISOString(),
                        totalDbOrders: dbOrders.length,
                        orders: dbOrders.map(o => ({
                            id: o.id,
                            name: o.name,
                            state: o.state,
                            server_id: o.server_id,
                            finalized: o.finalized
                        }))
                    };
                    
                    console.log(`📊 [${label}] Orders in localStorage:`, state.totalDbOrders);
                    state.orders.forEach(o => {
                        console.log(`   - ${o.name} (${o.id}) State: ${o.state}, Server ID: ${o.server_id}, Finalized: ${o.finalized}`);
                    });
                    
                    window.orderStates.push(state);
                    return state;
                };
                
                // Hook into order removal
                if (pos.db && pos.db.remove_order) {
                    const originalRemove = pos.db.remove_order;
                    pos.db.remove_order = function(orderId) {
                        console.log('🗑️ REMOVING ORDER FROM DB:', orderId);
                        console.trace('Call stack for order removal');
                        return originalRemove.call(this, orderId);
                    };
                }
                
                // Hook into _save_to_server
                if (pos._save_to_server) {
                    const original_save = pos._save_to_server;
                    pos._save_to_server = function(orders, options) {
                        console.log('🔄 _save_to_server called for orders:', orders.map(o => o.name));
                        window.captureState('before_save_to_server');
                        
                        const result = original_save.call(this, orders, options);
                        
                        result.then(serverIds => {
                            console.log('✅ _save_to_server SUCCESS. Server IDs:', serverIds);
                            setTimeout(() => window.captureState('after_save_success'), 100);
                            return serverIds;
                        }).catch(error => {
                            console.log('❌ _save_to_server FAILED:', error);
                            setTimeout(() => window.captureState('after_save_error'), 100);
                            throw error;
                        });
                        
                        return result;
                    };
                }
                
                // Initial state
                window.captureState('initial');
            };
            
            waitForPos();
        });
        
        console.log('\n🎯 === READY FOR MANUAL TESTING ===');
        console.log('1. Manually add items to cart');
        console.log('2. Click Payment button (bottom left)');
        console.log('3. Select Cash payment method');
        console.log('4. Click Validate');
        console.log('5. Watch the console output for duplicate order detection');
        console.log('\nDebug commands available in DevTools Console:');
        console.log('- window.captureState("my_label") - Capture current state');
        console.log('- window.orderStates - View all captured states');
        
        // Wait for manual testing
        await page.waitForTimeout(600000); // 10 minutes for manual testing
        
    } catch (error) {
        console.error('❌ Error:', error);
    }
    
    console.log('Session complete. Press Ctrl+C to close.');
    await new Promise(() => {}); // Keep open until manually closed
}

process.on('SIGINT', () => {
    console.log('\n👋 Closing...');
    process.exit(0);
});

simpleDebug().catch(console.error);