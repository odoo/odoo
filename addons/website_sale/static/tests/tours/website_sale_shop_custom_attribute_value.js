    import { registry } from "@web/core/registry";

    registry.category("web_tour.tours").add("shop_custom_attribute_value", {
        url: "/shop?search=Customizable Desk",
        steps: () => [{
        content: "click on Customizable Desk",
        trigger: '.oe_product_cart a:contains("Customizable Desk (TEST)")',
        run: "click",
        expectUnloadPage: true,
    },
    {
        trigger: "li.js_attribute_value",
    },
    {
        trigger: 'li.js_attribute_value span:contains(Custom)',
        run: 'click',
    }, {
        trigger: 'input.variant_custom_value',
        run: "edit Wood",
    }, {
        id: 'add_cart_step',
        trigger: 'a:contains(Add to cart)',
        run: 'click',
    },
    {
        trigger: 'button:contains(Go to Checkout)',
        run: 'click',
        expectUnloadPage: true,
    },
    {
        trigger: "#cart_products",
    },
    {
        trigger: 'span:contains(Custom: Wood)',
    }]});
