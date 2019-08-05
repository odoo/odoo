odoo.define('pos_hr.tour.login_with_employees', function (require) {
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

    var steps = [{
        content: 'waiting for loading to finish',
        trigger: 'body:has(.loader:hidden)',
        run: function () {},
    }]

    // Login with an employee with no manager rights
    // Check if close button is hidden
    // Check if price control is disabled
    steps = steps.concat(login_with_employee('Abigail Peterson', false));
    steps = steps.concat([{
        content: 'Check close button hidden',
        trigger: 'body:not(.header-button:contains("Close"))',
        run: function() {},
    }, {
        content: 'Check price control is disabled',
        trigger: '.mode-button:contains("Price").disabled-mode',
        run: function() {},
    }]);

    // Lock sression and check there is no close session button in the lockscreen
    steps = steps.concat([{
        content: 'Lock session',
        trigger: '.fa-unlock',
        run: 'click',
    }, { 
        content: 'Check lock-window is shown without close button',
        trigger: '.login-overlay:not(.close-session)',
        run: function(){},
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

    Tour.register('pos_hr', { test: true, url: '/pos/web' }, steps);
});
