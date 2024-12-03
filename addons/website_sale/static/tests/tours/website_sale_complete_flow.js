/** @odoo-module **/

    import { rpc } from "@web/core/network/rpc";
    import { registry } from "@web/core/registry";
    import * as tourUtils from "@website_sale/js/tours/tour_utils";

    registry.category("web_tour.tours").add('website_sale_tour_1', {
        checkDelay: 150,
        url: '/shop?search=Storage Box Test',
        steps: () => [
    // Testing b2c with Tax-Excluded Prices
    {
        content: "Open product page",
        trigger: '.oe_product_cart a:contains("Storage Box Test")',
        run: "click",
    },
    {
        content: "Add one more storage box",
        trigger: '.js_add_cart_json:eq(1)',
        run: "click",
    },
    {
        content: "Check b2b Tax-Excluded Prices",
        trigger: ".product_price .oe_price .oe_currency_value:contains(/^79.00$/)",
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
        run: "click",
    },
        tourUtils.goToCart({quantity: 2}),
    {
        content: "Check for 2 products in cart",
        trigger:
            '#cart_products div:has(a>h6:contains("Storage Box Test")) input.js_quantity:value(2)',
    },
    ...tourUtils.assertCartAmounts({
        taxes: '23.70',
        untaxed: '158.00',
        total: '181.70',
    }),
    {
        content: "Proceed to checkout",
        trigger: 'a[href*="/shop/checkout"]',
        run: "click",
    },
    {
        content: "Fulfill delivery address form",
        trigger: 'select[name="country_id"]',
        run: "selectByLabel Afghanistan",
    },
    {
        trigger: `input[name="name"]`,
        run: "edit abcd",
    },
    {
        trigger: `input[name="phone"]`,
        run: "edit 99999999",
    },
    {
        trigger: `input[name="email"]`,
        run: "edit abc@odoo.com",
    },
    {
        trigger: `input[name="street"]`,
        run: "edit SO1 Delivery Street, 33",
    },
    {
        trigger: `input[name="city"]`,
        run: "edit SO1DeliveryCity",
    },
    {
        trigger: `input[name="zip"]`,
        run: "edit 10000",
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Continue checkout")',
        run: "click",
    },
    {
        content: "Click for edit address",
        trigger: 'a:contains("Edit") i',
        run: "click",
    },
    {
        content: "Billing address is not same as delivery address",
        trigger: '#use_delivery_as_billing',
        run: "click",
    },
    {
        content: "Add a billing address",
        trigger: '.all_billing a[href^="/shop/address"]:contains("Add address")',
        run: "click",
    },
    {
        trigger: 'h3:contains("Billing address")',
    },
    {
        content: "Fulfill billing address form",
        trigger: 'select[name="country_id"]',
        run: "selectByLabel Afghanistan",
    },
    {
        trigger: `input[name="name"]`,
        run: "edit def",
    },
    {
        trigger: `input[name="phone"]`,
        run: "edit 8888888888",
    },
    {
        trigger: `input[name="email"]`,
        run: "edit abc@odoo.com",
    },
    {
        trigger: `input[name="street"]`,
        run: "edit 17, SO1 Billing Road",
    },
    {
        trigger: `input[name="city"]`,
        run: "edit SO1BillingCity",
    },
    {
        trigger: `input[name="zip"]`,
        run: "edit 10000",
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Save address")',
        run: "click",
    },
    {
        content: "Check selected delivery address is same as typed in previous step",
        trigger: '#delivery_address_row:contains(SO1 Delivery Street, 33):contains(SO1DeliveryCity):contains(Afghanistan)',
    },
    {
        content: "Check selected billing address is same as typed in previous step",
        trigger: '#billing_address_row:contains(17, SO1 Billing Road):contains(SO1BillingCity):contains(Afghanistan)',
    },
    {
        content: "Click for edit address",
        trigger: 'a:contains("Edit") i',
        run: "click",
    },
    {
        content: "Click for edit billing address",
        trigger: '.all_billing .js_edit_address:first',
        run: "click",
    },
    {
        trigger: 'h3:contains("Billing address")',
    },
    {
        content: "Change billing address form",
        trigger: 'select[name="country_id"]',
    },
    {
        trigger: `input[name="name"]`,
        run: "edit abcd",
    },
    {
        trigger: `input[name="phone"]`,
        run: "edit 11111111",
    },
    {
        trigger: `input[name="street"]`,
        run: "edit SO1 Billing Street Edited, 33",
    },
    {
        trigger: `input[name="city"]`,
        run: "edit SO1BillingCityEdited",
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Save address")',
        run: "click",
    },
        tourUtils.confirmOrder(),
    {
        content: "Check selected billing address is same as typed in previous step",
        trigger: '#billing_address_row:contains(SO1 Billing Street Edited, 33):contains(SO1BillingCityEdited):contains(Afghanistan)',
    },
    {
        content: "Select `Wire Transfer` payment method",
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
        run: "click",
    },
    {
        trigger:
            'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]:checked',
    },
    {
        content: "Pay Now",
        trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
        run: "click",
    },
    {
        content: "Sign up",
        trigger: '.oe_cart a:contains("Sign Up")',
        run: "click",
    },
    {
        trigger: `.oe_signup_form input[name="password"]`,
        run: "edit 1admin@admin",
    },
    {
        trigger: `.oe_signup_form input[name="confirm_password"]`,
        run: "edit 1admin@admin",
    },
    {
        content: "Submit login",
        trigger: `.oe_signup_form button[type="submit"]`,
        run: "click",
    },
    {
        content: "See Quotations",
        trigger: '.o_portal_docs a:contains("Quotations to review")',
        run: "click",
    },
    // Sign in as admin change config auth_signup -> b2b, sale_show_tax -> total and Logout
    {
        trigger: ".o_header_standard:not(.o_transitioning)",
    },
    {
        content: "Open Dropdown for logout",
        trigger: 'header#top li.dropdown:visible a:contains("abcd")',
        run: "click",
    },
    {
        content: "Logout",
        trigger: '#o_logout:contains("Logout")',
        run: "click",
    },
    {
        content: "Sign in as admin",
        trigger: 'header a[href="/web/login"]',
        run: "click",
    },
    {
        trigger: `.oe_login_form input[name="login"]`,
        run: "edit admin",
    },
    {
        trigger: `.oe_login_form input[name="password"]`,
        run: "edit admin",
    },
    {
        trigger: `.oe_login_form input[name="redirect"]:not(:visible)`,
        run(helpers) {
            this.anchor.value = "/";
        },
    },
    {
        content: "Submit login",
        trigger: `.oe_login_form button[type="submit"]`,
        run: "click"
    },
    {
        trigger: ".o_frontend_to_backend_nav", // Check if the user is connected
    },
    {
        content: "Configuration Settings for 'Tax Included' and sign up 'On Invitation'",
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
        run: "click",
    },
    {
        content: "Add one more Storage Box Test",
        trigger: '.js_add_cart_json:eq(1)',
        run: "click",
    },
    {
        content: "Check b2c Tax-Included Prices",
        trigger: ".product_price .oe_price .oe_currency_value:contains(/^90.85$/)",
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
        run: "click",
    },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Check for 2 products in cart",
            trigger:
                '#cart_products div:has(a>h6:contains("Storage Box Test")) input.js_quantity:value(2)',
        },
        ...tourUtils.assertCartAmounts({
            taxes: "23.70",
            untaxed: "158.00",
            total: "181.70",
        }),
        {
            content: "Proceed to checkout",
            trigger: 'a[href*="/shop/checkout"]',
            run: "click",
        },
    {
        content: "Click on Sign in Button",
        trigger: `.oe_cart a:contains(Sign in)`,
        run: "click",
    },
    {
        trigger: `.oe_login_form input[name="login"]`,
        run: "edit abc@odoo.com",
    },
    {
        trigger: `.oe_login_form input[name="password"]`,
        run: "edit 1admin@admin",
    },
    {
        content: "Submit login",
        trigger: `.oe_login_form button[type="submit"]`,
        run: "click",
    },
    {
        content: "Add new delivery address",
        trigger: '.all_delivery a[href^="/shop/address"]:contains("Add address")',
        run: "click",
    },
    {
        content: "Fulfill delivery address form",
        trigger: 'select[name="country_id"]',
        run: "selectByLabel Afghanistan",
    },
    {
        trigger: `input[name="name"]`,
        run: "edit ghi",
    },
    {
        trigger: `input[name="phone"]`,
        run: "edit 7777777777",
    },
    {
        trigger: `input[name="street"]`,
        run: "edit SO2New Delivery Street, 5",
    },
    {
        trigger: `input[name="city"]`,
        run: "edit SO2NewDelivery",
    },
    {
        trigger: `input[name="zip"]`,
        run: "edit 1200",
    },
    {
        content: "Click on next button",
        trigger: '.oe_cart .btn:contains("Save address")',
        run: "click",
    },
    {
        content: "Select `Wire Transfer` payment method",
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
        run: "click",
    },
    {
        trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]:checked',
    },
    {
        content: "Pay Now",
        trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
        run: "click",
    },
    {
        trigger: '.oe_cart .oe_website_sale_tx_status',
    },
    {
        content: "Open Dropdown for See quotation",
        trigger: 'header#top li.dropdown:visible a:contains("abc")',
        run: "click",
    },
    {
        trigger: "header#top li.dropdown .js_usermenu.show",
    },
    {
        content: "My account",
        trigger: 'header#top .dropdown-menu a[href="/my/home"]:visible',
        run: "click",
    },

    // enable extra step on website checkout and check extra step on checkout process
    {
        trigger: ".o_header_standard:not(.o_transitioning)",
    },
    {
        content: "Open Dropdown for logout",
        trigger: 'header#top li.dropdown:visible a:contains("abc")',
        run: "click",
    },
    {
        content: "Logout",
        trigger: '#o_logout:contains("Logout")',
        run: "click",
    },
    {
        content: "Sign in as admin",
        trigger: 'header a[href="/web/login"]',
        run: "click",
    },
    {
        trigger: `.oe_login_form input[name="login"]`,
        run: "edit admin",
    },
    {
        trigger: `.oe_login_form input[name="password"]`,
        run: "edit admin",
    },
    {
        trigger: `.oe_login_form input[name="redirect"]:not(:visible)`,
        run(helpers) {
            this.anchor.value = "/shop/cart";
        },
    },
    {
        content: "Submit login",
        trigger: `.oe_login_form button[type="submit"]`,
        run: "click",
    }]});

    registry.category("web_tour.tours").add('website_sale_tour_2', {
        url: '/shop/cart',
        checkDelay: 150,
        steps: () => [
    {
        trigger: '.o_wizard:contains("Extra Info")',
    },
    {
        content: "Open Dropdown for logout",
        trigger: 'header#top li.dropdown:visible a:contains("Mitchell Admin")',
        run: "click",
    },
    {
        content: "Logout",
        trigger: '#o_logout:contains("Logout")',
        run: "click",
    },
    {
        content: "Sign in as abc",
        trigger: 'header a[href="/web/login"]',
        run: "click",
    },
    {
        trigger: `.oe_login_form input[name="login"]`,
        run: "edit abc@odoo.com",
    },
    {
        trigger: `.oe_login_form input[name="password"]`,
        run: "edit 1admin@admin",
    },
    {
        trigger: `.oe_login_form input[name="redirect"]:not(:visible)`,
        run(helpers) {
            this.anchor.value = "/shop?search=Storage Box Test";
        },
    },
    {
        content: "Submit login",
        trigger: `.oe_login_form button[type="submit"]`,
        run: "click",
    },
    {
        content: "Open product page",
        trigger: '.oe_product_cart a:contains("Storage Box Test")',
        run: "click",
    },
    {
        content: "Click on add to cart",
        trigger: '#add_to_cart',
        run: "click",
    },
        tourUtils.goToCart(),
        tourUtils.goToCheckout(),
    {
        content: "Click on 'Continue checkout' button",
        trigger: '.oe_cart .btn:contains("Continue checkout")',
        run: "click",
    },
    ...tourUtils.payWithTransfer(),
    {
        content: "Check payment status confirmation window",
        trigger: ".oe_website_sale_tx_status[data-order-tracking-info]",
    }]});
