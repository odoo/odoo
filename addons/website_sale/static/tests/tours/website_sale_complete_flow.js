/** @odoo-module **/

    import { rpc } from "@web/core/network/rpc";
    import { registry } from "@web/core/registry";
    import tourUtils from "@website_sale/js/tours/tour_utils";

    registry.category("web_tour.tours").add('website_sale_tour_1', {
        test: true,
        checkDelay: 250,
        url: '/shop?search=Storage Box Test',
        steps: () => [
    // Testing b2c with Tax-Excluded Prices
    {
        content: "Open product page",
        trigger: '.oe_product_cart a:contains("Storage Box Test")',
    },
    {
        content: "Add one more storage box",
        trigger: '.js_add_cart_json:eq(1)',
    },
    {
        content: "Check b2b Tax-Excluded Prices",
        trigger: ".product_price .oe_price .oe_currency_value:contains(/^79.00$/)",
        run: function () {}, // it's a check
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
    },
        tourUtils.goToCart({quantity: 2}),
    {
        content: "Check for 2 products in cart and proceed to checkout",
        extra_trigger: '#cart_products div:has(a>h6:contains("Storage Box Test")) input.js_quantity:value(2)',
        trigger: 'a[href*="/shop/checkout"]',
    },
    ...tourUtils.assertCartAmounts({
        taxes: '23.70',
        untaxed: '158.00',
        total: '181.70',
    }),
    {
        content: "Fulfill billing address form",
        trigger: 'select[name="country_id"]',
        run: function () {
            document.querySelector('input[name="name"]').value = 'abc';
            document.querySelector('input[name="phone"]').value = '99999999';
            document.querySelector('input[name="email"]').value = 'abc@odoo.com';
            document.querySelector('input[name="street"]').value = 'SO1 Billing Street, 33';
            document.querySelector('input[name="city"]').value = 'SO1BillingCity';
            document.querySelector('input[name="zip"]').value = '10000';
            document.querySelectorAll("#country_id option")[1].selected = true;
        },
    },
    {
        content: "Shipping address is not same as billing address",
        trigger: '#shipping_use_same',
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Continue checkout")',
    },
    {
        content: "Fulfill shipping address form",
        trigger: 'select[name="country_id"]',
        extra_trigger: 'h3:contains("Shipping address")',
        run: function () {
            document.querySelector('input[name="name"]').value = 'def';
            document.querySelector('input[name="phone"]').value = '8888888888';
            document.querySelector('input[name="street"]').value = '17, SO1 Shipping Road';
            document.querySelector('input[name="city"]').value = 'SO1ShippingCity';
            document.querySelector('input[name="zip"]').value = '10000';
            document.querySelectorAll("#country_id option")[1].selected = true;
        },
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Save address")',
    },
    {
        content: "Check selected billing address is same as typed in previous step",
        trigger: '#shipping_and_billing:contains(SO1 Billing Street, 33):contains(SO1BillingCity):contains(Afghanistan)',
        run: function () {}, // it's a check
    },
    {
        content: "Check selected shipping address is same as typed in previous step",
        trigger: '#shipping_and_billing:contains(17, SO1 Shipping Road):contains(SO1ShippingCity):contains(Afghanistan)',
        run: function () {}, // it's a check
    },
    {
        content: "Click for edit address",
        trigger: 'a:contains("Edit") i',
    },
    {
        content: "Click for edit billing address",
        trigger: '.js_edit_address:first',
    },
    {
        content: "Change billing address form",
        trigger: 'select[name="country_id"]',
        extra_trigger: 'h3:contains("Billing address")',
        run: function () {
            document.querySelector('input[name="name"]').value = 'abcd';
            document.querySelector('input[name="phone"]').value = '11111111';
            document.querySelector('input[name="street"]').value = 'SO1 Billing Street Edited, 33';
            document.querySelector('input[name="city"]').value = 'SO1BillingCityEdited';
        },
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Save address")',
    },
    {
        content: "Confirm Address",
        trigger: 'a.btn:contains("Confirm")',
    },
    {
        content: "Check selected billing address is same as typed in previous step",
        trigger: '#shipping_and_billing:contains(SO1 Billing Street Edited, 33):contains(SO1BillingCityEdited):contains(Afghanistan)',
        run: function () {}, // it's a check
    },
    {
        content: "Select `Wire Transfer` payment method",
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
    },
    {
        content: "Pay Now",
        extra_trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]:checked',
        trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
    },
    {
        content: "Sign up",
        trigger: '.oe_cart a:contains("Sign Up")',
    },
    {
        content: "Submit login",
        trigger: '.oe_signup_form',
        run: function () {
            document.querySelector('.oe_signup_form input[name="password"]').value = "1admin@admin";
            document.querySelector('.oe_signup_form input[name="confirm_password"]').value = "1admin@admin";
            document.querySelector('.oe_signup_form').submit();
        },
    },
    {
        content: "See Quotations",
        trigger: '.o_portal_docs a:contains("Quotations to review")',
    },
    // Sign in as admin change config auth_signup -> b2b, sale_show_tax -> total and Logout
    {
        content: "Open Dropdown for logout",
        extra_trigger: ".o_header_standard:not(.o_transitioning)",
        trigger: 'header#top li.dropdown:visible a:contains("abcd")',
    },
    {
        content: "Logout",
        trigger: '#o_logout:contains("Logout")',
    },
    {
        content: "Sign in as admin",
        trigger: 'header a[href="/web/login"]',
    },
    {
        content: "Submit login",
        trigger: '.oe_login_form',
        run: function () {
            document.querySelector('.oe_login_form input[name="login"]').value = "admin";
            document.querySelector('.oe_login_form input[name="password"]').value = "admin";
            document.querySelector('.oe_login_form input[name="redirect"]').value = "/";
            document.querySelector('.oe_login_form').submit();
        },
    },
    {
        content: "Configuration Settings for 'Tax Included' and sign up 'On Invitation'",
        extra_trigger: '.o_frontend_to_backend_nav', // Check if the user is connected
        trigger: '#wrapwrap',
        run: function () {
            var def1 = rpc(`/web/dataset/call_kw/res.config.settings/create`, {
                model: "res.config.settings",
                method: "create",
                args: [{
                    'auth_signup_uninvited': 'b2b',
                    'show_line_subtotals_tax_selection': 'tax_included',
                }],
                kwargs: {},
            });
            var def2 = def1.then(function (resId) {
                return rpc(`/web/dataset/call_kw/res.config.settings/execute`, {
                    model: "res.config.settings",
                    method: "execute",
                    args: [[resId]],
                    kwargs: {},
                });
            });
            def2.then(function () {
                window.location.href = '/web/session/logout?redirect=/shop?search=Storage Box Test';
            });
        },
    },
    // Testing b2b with Tax-Included Prices
    {
        content: "Open product page",
        trigger: '.oe_product_cart a:contains("Storage Box Test")',
    },
    {
        content: "Add one more Storage Box Test",
        trigger: '.js_add_cart_json:eq(1)',
    },
    {
        content: "Check b2c Tax-Included Prices",
        trigger: ".product_price .oe_price .oe_currency_value:contains(/^90.85$/)",
        run: function () {}, // it's a check
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
    },
        tourUtils.goToCart({quantity: 2}),
    {
        content: "Check for 2 products in cart and proceed to checkout",
        extra_trigger: '#cart_products div:has(a>h6:contains("Storage Box Test")) input.js_quantity:value(2)',
        trigger: 'a[href*="/shop/checkout"]',
    },
    ...tourUtils.assertCartAmounts({
        taxes: '23.70',
        untaxed: '158.00',
        total: '181.70',
    }),
    {
        content: "Click on Sign in Button",
        trigger: `.oe_cart a:contains(Sign in)`,
    },
    {
        content: "Submit login",
        trigger: '.oe_login_form',
        run: function () {
            document.querySelector('.oe_login_form input[name="login"]').value = "abc@odoo.com";
            document.querySelector('.oe_login_form input[name="password"]').value = "1admin@admin";
            document.querySelector('.oe_login_form').submit();
        },
    },
    {
        content: "Add new shipping address",
        trigger: '.all_shipping a[href^="/shop/address"]:contains("Add address")',
    },
    {
        content: "Fulfill shipping address form",
        trigger: 'select[name="country_id"]',
        run: function () {
            document.querySelector('input[name="name"]').value = 'ghi';
            document.querySelector('input[name="phone"]').value = '7777777777';
            document.querySelector('input[name="street"]').value = 'SO2New Shipping Street, 5';
            document.querySelector('input[name="city"]').value = 'SO2NewShipping';
            document.querySelector('input[name="zip"]').value = '1200';
            document.querySelectorAll("#country_id option")[1].selected = true;
        },
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Save address")',
    },
    {
        content: "Select `Wire Transfer` payment method",
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
    },
    {
        content: "Pay Now",
        extra_trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]:checked',
        trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
    },
    {
        content: "Open Dropdown for See quotation",
        extra_trigger: '.oe_cart .oe_website_sale_tx_status',
        trigger: 'header#top li.dropdown:visible a:contains("abc")',
    },
    {
        content: "My account",
        extra_trigger: 'header#top li.dropdown .js_usermenu.show',
        trigger: 'header#top .dropdown-menu a[href="/my/home"]:visible',
    },

    // enable extra step on website checkout and check extra step on checkout process
    {
        content: "Open Dropdown for logout",
        extra_trigger: ".o_header_standard:not(.o_transitioning)",
        trigger: 'header#top li.dropdown:visible a:contains("abc")',
    },
    {
        content: "Logout",
        trigger: '#o_logout:contains("Logout")',
    },
    {
        content: "Sign in as admin",
        trigger: 'header a[href="/web/login"]',
    },
    {
        content: "Submit login",
        trigger: '.oe_login_form',
        run: function () {
            document.querySelector('.oe_login_form input[name="login"]').value  = "admin";
            document.querySelector('.oe_login_form input[name="password"]').value  = "admin";
            document.querySelector('.oe_login_form input[name="redirect"]').value  = "/shop/cart";
            document.querySelector('.oe_login_form').submit();
        },
    }]});

    registry.category("web_tour.tours").add('website_sale_tour_2', {
        test: true,
        url: '/shop/cart',
        steps: () => [
    {
        content: "Open Dropdown for logout",
        extra_trigger: '.o_wizard:contains("Extra Info")',
        trigger: 'header#top li.dropdown:visible a:contains("Mitchell Admin")',
    },
    {
        content: "Logout",
        trigger: '#o_logout:contains("Logout")',
    },
    {
        content: "Sign in as abc",
        trigger: 'header a[href="/web/login"]',
    },
    {
        content: "Submit login",
        trigger: '.oe_login_form',
        run: function () {
            document.querySelector('.oe_login_form input[name="login"]').value = "abc@odoo.com";
            document.querySelector('.oe_login_form input[name="password"]').value = "1admin@admin";
            document.querySelector('.oe_login_form input[name="redirect"]').value = "/shop?search=Storage Box Test";
            document.querySelector('.oe_login_form').submit();
        },
    },
    {
        content: "Open product page",
        trigger: '.oe_product_cart a:contains("Storage Box Test")',
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
    },
        tourUtils.goToCart(),
        tourUtils.goToCheckout(),
    {
        content: "Click on 'Continue checkout' button",
        trigger: '.oe_cart .btn:contains("Continue checkout")',
    },
    {
        content: "Check selected billing address is same as typed in previous step",
        trigger: '#shipping_and_billing:contains(SO1 Billing Street Edited, 33):contains(SO1BillingCityEdited):contains(Afghanistan)',
        run: function () {}, // it's a check
    },
    {
        content: "Check selected shipping address is same as typed in previous step",
        trigger: '#shipping_and_billing:contains(SO2New Shipping Street, 5):contains(SO2NewShipping):contains(Afghanistan)',
        run: function () {}, // it's a check
    },
    ...tourUtils.payWithTransfer(),
    {
        content: "Check payment status confirmation window",
        trigger: ".oe_website_sale_tx_status[data-order-tracking-info]",
        isCheck: true,
    }]});
