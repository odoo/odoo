import { registry } from '@web/core/registry';
import { clickOnEditAndWaitEditMode } from '@website/js/tours/tour_utils';

registry.category('web_tour.tours').add('website_sale.product_editor_seo_dialog', {
    steps: () => [
        {
            content: "trigger website backend",
            trigger: ".o_frontend_to_backend_edit_btn",
            run: "click",
            expectUnloadPage: true,
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "drag & drop intro snippet into description_ecommerce field",
            trigger: ".o_snippet[name='Intro'] .o_snippet_thumbnail_area",
            run: "drag_and_drop :iframe div[data-oe-field='description_ecommerce'] .oe_drop_zone",
        },
        {
            content: "select intro snippet type",
            trigger: ".modal-body :iframe div[data-snippet-id='s_banner']",
            run: "click",
        },
        {
            content: "check the snippet has been dropped to the correct field",
            trigger: ":iframe div[data-oe-field='description_ecommerce'] .s_banner",
        },
        {
            content: "save edited product page",
            trigger: "button[data-action='save']",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "drag & drop intro snippet into website_description field",
            trigger: ".o_snippet[name='Intro'] .o_snippet_thumbnail_area",
            run: "drag_and_drop :iframe div#product_full_description",
        },
        {
            content: "select intro snippet type",
            trigger: ".modal-body :iframe div[data-snippet-id='s_banner']",
            run: "click",
        },
        {
            content: "check the snippet has been dropped to the correct field",
            trigger: ":iframe div#product_full_description .s_banner",
        },
        {
            content: "save edited product page",
            trigger: "button[data-action='save']",
            run: "click",
        },
        {
            content: "click on the site menu",
            trigger: "button[data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "click on the 'Optimize SEO' menu item",
            trigger: "a[data-menu-xmlid='website.menu_optimize_seo']",
            run: "click",
        },
        {
            content: "check if the Optimize SEO modal is successfully triggered",
            trigger: ".oe_seo_configuration",
        },
    ],
});
