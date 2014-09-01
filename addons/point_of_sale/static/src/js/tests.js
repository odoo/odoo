(function() {
    'use strict';

    openerp.Tour.register({
        id: 'pos_basic_order',
        name: 'Complete a basic order trough the Front-End',
        path: '/web#model=pos.session.opening&action=point_of_sale.action_pos_session_opening',
        mode: 'test',
        steps: [
            {
                title:   'Wait fot the bloody screen to be ready',
                wait: 200,
            },
            {
                title:  'Load the Session',
                waitNot: '.oe_loading:visible',
                element: 'span:contains("Resume Session"),span:contains("Start Session")',
            },
            {
                title: 'Loading the Loading Screen',
                waitFor: '.loader'
            },
            {
                title: 'Waiting for the end of loading...',
                waitFor: '.loader:hidden',
            },
            {
                title: 'Loading The Point of Sale',
                waitFor: '.pos',
            },
            {
                title: 'On va manger des CHIPS!',
                element: '.product-list .product-name:contains("250g Lays Pickels")',
            },
            {
                title: 'The chips have been added to the Order',
                waitFor: '.order .product-name:contains("250g Lays Pickels")',
            },
            {
                title: 'The order total has been updated to the correct value',
                wait: 2000,
                waitFor: '.order .total .value:contains("1.48 €")',
            },
            {
                title: "Let's buy more chips",
                element: '.product-list .product-name:contains("250g Lays Pickels")',
            },
            {
                title: "Let's veryify we pay the correct price for two bags of chips",
                waitFor: '.order .total .value:contains("2.96 €")',
            },
            {
                title: "Let's pay with a debit card",
                element: ".paypad-button:contains('Bank')",
            },
            {
                title: "Let's accept the payment",
                onload: function(){ 
                    // The test cannot validate or cancel the print() ... so we replace it by a noop !.
                    window._print = window.print;
                    window.print  = function(){ console.log('Print!') };
                },
                element: ".button .iconlabel:contains('Validate'):visible",
            },
            {
                title: "Let's finish the order",
                element: ".button:not(.disabled) .iconlabel:contains('Next'):visible",
            },
            {
                onload: function(){
                    window.print  = window._print;
                    window._print = undefined;
                },
                title: "Let's wait for the order posting",
                waitFor: ".oe_status.js_synch .js_connected:visible",
            },
            {
                title: "Let's close the Point of Sale",
                element: ".header-button:contains('Close')",
            },
            {
                title: "Wait for the backend to ready itself",
                element: 'span:contains("Resume Session"),span:contains("Start Session")',
            },
        ],
    });

})();

