import { registry } from '@web/core/registry';
import * as tourUtils from '@website/js/tours/tour_utils';

const snippets = [
    's_banner',
    's_text_image',
    's_image_text',
    's_picture',
    's_title',
    's_masonry_block_default_template',
    's_company_team',
    's_showcase',
    's_quotes_carousel',
];

// Function to generate tour steps for validating snippets
export function generateSnippetValidationSteps(snippets) {
    return snippets.map(snippet => ({
        content: `finding ${snippet} snippet in homepage`,
        trigger: `:iframe section[data-snippet="${snippet}"]`,
    }));
}

registry.category('web_tour.tours').add('website_sale_configurator', {
    url: '/website/configurator',
    steps: () => [
        ...tourUtils.websiteConfiguratorDescription("online_store", "ab", "abbey", "sell_more"),
        tourUtils.websiteConfiguratorPalette("#F8FBFF"),
        {
            content: "Click on build my website",
            trigger: 'button.btn-primary',
            run: "click",
        },
        ...tourUtils.websiteConfiguratorLoadHomePage(),
        // Validate presence of E-commerce specific snippets in the homepage
        ...generateSnippetValidationSteps(snippets),
    ]
});
