odoo.define('pos_restaurant_hr.tour.login_with_employees', function (require) {
    "use strict";

    var Tour = require("web_tour.tour");

    function generate_keypad_steps(amount_str, keypad_selector) {
        var steps = [];
        var i;
        for (i = 0; i < amount_str.length; ++i) {
            var current_char = amount_str[i];
            steps = steps.concat([{
                content: 'press ' + current_char + ' on payment keypad',
                trigger: keypad_selector + ' .input-button:contains("' + current_char + '"):visible'
            }]);
        }

        return steps;
    }

    function generate_pin_keypad_steps(pin) {
        return generate_keypad_steps(pin, '.popup-password');
    }

    function login_with_employee(name, pin) {
        var steps = [{
            content: 'Click on Select Cashier',
            trigger: '.select-employee',
            run: 'click',
        }, {
            content: 'Select ' + name,
            trigger: '.selection-item:contains("' + name + '")'
        }];
        if (pin !== false) {
            steps = steps.concat(generate_keypad_steps(pin, '.popup-password'));
            steps = steps.concat([{
                content: 'Confirm password',
                trigger: '.popup-password .confirm',
                run: 'click',
            }]);

        }
        return steps;
    }

    function open_table(table_id, order_count) {
        order_count = order_count || null;
        var steps = [{
            content: 'open table ' + table_id,
            trigger: '.label:contains(' + table_id +')',
            run: 'click',
        }];
        if (order_count !== null){
            steps = steps.concat(verify_orders_synced(order_count));
        }
        return steps;
    }

    var steps = [{
        content: 'waiting for loading to finish',
        trigger: 'body:has(.loader:hidden)',
        run: function () {},
    }]

    // Login with an employee with no manager rights
    // Check if close button is hidden
    steps = steps.concat(login_with_employee('Abigail Peterson', false));
    steps = steps.concat([{
        content: 'Check close button hidden',
        trigger: 'body:not(.header-button:contains("Close"))',
        run: function() {},
    }]);
    steps = steps.concat(open_table('T5'));

    // Check if session gets locked automatically if nothing is done for a configured period.
    // the timeout to find the trigger is used as the time nothing is done.
    steps = steps.concat([{
        content: 'Wait for floor screen',
        trigger: '.floor-screen',
        run: function() {},
    }, {
        content: 'Wait for session to lock',
        trigger: '.select-employee',
        run: function() {},
    }]);

    // Login with an admin
    // check price control is enabled
    // Close the session with the visible close button
    steps = steps.concat(login_with_employee('Mitchell Admin', '0000'));
    steps = steps.concat([{
        content: 'Check price control is enabled',
        trigger: 'body:not(.mode-button:contains("Price").disabled-mode)',
        run: function() {},
    }, {
        content: 'Check close button visible, click it',
        trigger: '.header-button:contains("Close")',
        run: 'click',
    }, {
        content: 'Confirm closing',
        trigger: '.header-button.confirm',
        run: 'click',
    }]);

    Tour.register('pos_restaurant_hr', { test: true, url: '/pos/web' }, steps);
});
