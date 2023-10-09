/** @odoo-module **/

    import { jsonrpc } from "@web/core/network/rpc_service";
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
        trigger: '.product_price .oe_price .oe_currency_value:containsExact(79.00)',
        run: function () {}, // it's a check
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
    },
        tourUtils.goToCart({quantity: 2}),
    {
        content: "Check for 2 products in cart and proceed to checkout",
        extra_trigger: '#cart_products div:has(a>h6:contains("Storage Box Test")) input.js_quantity:propValue(2)',
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
            $('input[name="name"]').val('abc');
            $('input[name="phone"]').val('99999999');
            $('input[name="email"]').val('abc@odoo.com');
            $('input[name="street"]').val('SO1 Billing Street, 33');
            $('input[name="city"]').val('SO1BillingCity');
            $('input[name="zip"]').val('10000');
            $('#country_id option:eq(1)').attr('selected', true);
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
            $('input[name="name"]').val('def');
            $('input[name="phone"]').val('8888888888');
            $('input[name="street"]').val('17, SO1 Shipping Road');
            $('input[name="city"]').val('SO1ShippingCity');
            $('input[name="zip"]').val('10000');
            $('#country_id option:eq(1)').attr('selected', true);
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
            $('input[name="name"]').val('abcd');
            $('input[name="phone"]').val('11111111');
            $('input[name="street"]').val('SO1 Billing Street Edited, 33');
            $('input[name="city"]').val('SO1BillingCityEdited');
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
            $('.oe_signup_form input[name="password"]').val("1admin@admin");
            $('.oe_signup_form input[name="confirm_password"]').val("1admin@admin");
            $('.oe_signup_form').submit();
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
            $('.oe_login_form input[name="login"]').val("admin");
            $('.oe_login_form input[name="password"]').val("admin");
            $('.oe_login_form input[name="redirect"]').val("/");
            $('.oe_login_form').submit();
        },
    },
    {
        content: "Configuration Settings for 'Tax Included' and sign up 'On Invitation'",
        extra_trigger: '.o_frontend_to_backend_nav', // Check if the user is connected
        trigger: '#wrapwrap',
        run: function () {
            var def1 = jsonrpc(`/web/dataset/call_kw/res.config.settings/create`, {
                model: "res.config.settings",
                method: "create",
                args: [{
                    'auth_signup_uninvited': 'b2b',
                    'show_line_subtotals_tax_selection': 'tax_included',
                }],
                kwargs: {},
            });
            var def2 = def1.then(function (resId) {
                return jsonrpc(`/web/dataset/call_kw/res.config.settings/execute`, {
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
        trigger: '.product_price .oe_price .oe_currency_value:containsExact(90.85)',
        run: function () {}, // it's a check
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
    },
        tourUtils.goToCart({quantity: 2}),
    {
        content: "Check for 2 products in cart and proceed to checkout",
        extra_trigger: '#cart_products div:has(a>h6:contains("Storage Box Test")) input.js_quantity:propValue(2)',
        trigger: 'a[href*="/shop/checkout"]',
    },
    ...tourUtils.assertCartAmounts({
        taxes: '23.70',
        untaxed: '158.00',
        total: '181.70',
    }),
    {
        content: "Click on Sign in Button",
        trigger: '.oe_cart a:contains(" Sign in")',
    },
    {
        content: "Submit login",
        trigger: '.oe_login_form',
        run: function () {
            $('.oe_login_form input[name="login"]').val("abc@odoo.com");
            $('.oe_login_form input[name="password"]').val("1admin@admin");
            $('.oe_login_form').submit();
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
            $('input[name="name"]').val('ghi');
            $('input[name="phone"]').val('7777777777');
            $('input[name="street"]').val('SO2New Shipping Street, 5');
            $('input[name="city"]').val('SO2NewShipping');
            $('input[name="zip"]').val('1200');
            $('#country_id option:eq(1)').attr('selected', true);
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
            $('.oe_login_form input[name="login"]').val("admin");
            $('.oe_login_form input[name="password"]').val("admin");
            $('.oe_login_form input[name="redirect"]').val("/shop/cart");
            $('.oe_login_form').submit();
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
            $('.oe_login_form input[name="login"]').val("abc@odoo.com");
            $('.oe_login_form input[name="password"]').val("1admin@admin");
            $('.oe_login_form input[name="redirect"]').val("/shop?search=Storage Box Test");
            $('.oe_login_form').submit();
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
