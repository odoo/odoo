import { registry } from "@web/core/registry";

var imageSelector = '#o-carousel-product .carousel-item.active img';
var imageName = "A Colorful Image";
var nameGreen = "Forest Green";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('website_sale.product_page_zoom', {
    url: '/shop?debug=1&search=' + imageName,
    steps: () => [
        {
            content: "select " + imageName,
            trigger: `.oe_product_cart a:text(${imageName})`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check that the product image has a srcset",
            trigger: imageSelector,
            run() {
                const img = document.querySelector(imageSelector);
                if (!img?.srcset) {
                    throw new Error('Image srcset attribute missing');
                }
                if (!img?.srcset.includes('image_512')) {
                    throw new Error('Srcset should list at least image_512');
                }
            },
        },
        {
            content: "click on the image",
            trigger: imageSelector,
            run: "click",
        },
        {
            content: "check that the image viewer opened",
            trigger: '.o_wsale_image_viewer',
        },
        {
            content: "close the image viewer",
            trigger: '.o_wsale_image_viewer_header span.fa-times',
            run: "click",
        },
        {
            content: "change variant",
            trigger: `input[data-attribute-name='Beautiful Color'][data-value-name='${nameGreen}']:not(:visible)`,
            run: 'click',
        },
        {
            content: "wait for variant to be loaded",
            trigger: '.oe_currency_value:contains("21.00")',
            run: "click",
        },
        {
            content: "click on the image",
            trigger: imageSelector,
            run: "click",
        },
        {
            content: "check there is a zoom on that big image",
            trigger: '.o_wsale_image_viewer',
        },
    ]
});
