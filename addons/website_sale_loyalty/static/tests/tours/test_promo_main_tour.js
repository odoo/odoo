import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_sale_loyalty', {
    url: '/shop?search=Small%20Cabinet',
    steps: () => [
        /* 1. Buy 1 Small Cabinet, enable coupon code & insert 10% code */
        {
            trigger: ".oe_search_found:not(:visible)",
        },
        {
            content: "select Small Cabinet",
            trigger: '.oe_product_cart a:contains("Small Cabinet")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "add 2 Small Cabinet into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "edit 2",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to cart)",
            run: "click",
        },
            tourUtils.goToCart({quantity: 2}),
        {
            trigger: 'form[name="coupon_code"]',
        },
        {
            content: "insert promo code 'testcode'",
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit testcode",
        },
        {
            content: "validate the coupon",
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check reward product",
            trigger: 'div>h6:contains("10.0% discount on total amount")',
        },
        {
            content: "check loyalty points",
            trigger: '.oe_website_sale_gift_card strong[name="o_loyalty_points"]:contains("372.03")',
        },
        /* 2. Add some cabinet to get a free one, play with quantity */
        {
            content: "go to shop",
            trigger: 'div>h6:contains("10.0% discount on total amount")',
            run: function () {
                rpc('/web/dataset/call_kw/account.tax/create', {
                    model: 'account.tax',
                    method: 'create',
                    args: [{
                      'name':'15% tax incl ' + new Date().getTime(),
                      'amount': 15,
                    }],
                    kwargs: {},
                }).then(function (tax_id) {
                    rpc('/web/dataset/call_kw/product.template/create', {
                        model: 'product.template',
                        method: 'create',
                        args: [{
                          'name': 'Taxed Product',
                          'taxes_id': [([6, false, [tax_id]])],
                          'list_price': 100,
                          'website_published': true,
                        }],
                        kwargs: {},
                    }).then(function (data) {
                        location.href = '/shop';
                    });
                });
            },
            expectUnloadPage: true,
        },
        ...tourUtils.addToCart({ productName: "Taxed Product", expectUnloadPage: true }),
            tourUtils.goToCart({quantity: 3}),
        {
            trigger: ".oe_currency_value:contains(/74.00/):not(div[name='o_cart_total'])",
        },
        {
            content: "check reduction amount got recomputed and merged both discount lines into one only",
            trigger: '.oe_website_sale .oe_cart',
        },
        /* 3. Add some cabinet to get a free one, play with quantity */
        {
            content: "add one Small Cabinet",
            trigger: '#cart_products input.js_quantity',
            run: "edit 3 && click body",
        },
        {
            content: "check reduction amount got recomputed when changing qty",
            trigger: '.oe_currency_value:contains("- 106.00")',
        },
        {
            content: "add more Small Cabinet into cart",
            trigger: '#cart_products input.js_quantity',
            run: "edit 4 && click body",
        },
        {
            content: "check free product is added",
            trigger: '#wrap:has(div h6:contains("Free Product - Small Cabinet"))',
        },
        {
            content: "remove one cabinet from cart",
            trigger: '#cart_products input.js_quantity[value="4"]',
            run: "edit 3 && click body",
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(div h6:contains("Free Product - Small Cabinet")))',
        },
        /* 4. Check /shop/payment does not break the `merged discount lines split per tax` (eg: with _compute_tax_ids) */
        {
            content: "go to checkout",
            trigger: 'a[href="/shop/checkout?try_skip_step=true"]',
            run: "click",
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartAmounts({
            total: '967.50',
        }),
    ]
});
