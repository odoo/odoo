/** @odoo-module **/

import { registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour(
    'product_unpublished_without_category',
    {
        url: '/',
    },
    () => [
        {
            trigger:'body:not(:has(.o_new_content_menu_choices)) .o_new_content_container > button',
            run: 'click',
        },
        {
            trigger: 'button[data-module-xml-id="base.module_website_sale"]',
            run: 'click',
        },
        {
            trigger: '.modal-dialog .o_field_widget[name="name"] input',
            run: 'edit Product Without Category',
        },
        {
            trigger: '.modal-footer button.btn-primary',
            run: 'click',
        },
        {
            trigger: 'body:not(:has(.modal))',
        },
        {
            trigger: ':iframe body:has(h1:contains("Product Without Category"))',
        },
    ]
);

registerWebsitePreviewTour(
    'product_published_with_category',
    {
        url: '/',
    },
    () => [
        {
            trigger:'body:not(:has(.o_new_content_menu_choices)) .o_new_content_container > button',
            run: 'click',
        },
        {
            trigger: 'button[data-module-xml-id="base.module_website_sale"]',
            run: 'click',
        },
        {
            trigger: '.modal-dialog .o_field_widget[name="name"] input',
            run: 'edit Product With Category',
        },
        {
            trigger: '.modal-dialog .o_field_widget[name="public_categ_ids"] input',
            run: 'edit Test',
        },
        {
            trigger: '.ui-autocomplete a:contains("Test Category")',
            run: 'click',
        },
        {
            trigger: '.modal-footer button.btn-primary',
            run: 'click',
        },
        {
            trigger: 'body:not(:has(.modal))',
        },
        {
            trigger: ':iframe body:has(h1:contains("Product With Category"))',
        },
    ]
);
