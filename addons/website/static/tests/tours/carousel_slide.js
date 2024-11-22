/** @odoo-module */
import { insertSnippet, registerWebsitePreviewTour, clickOnSave } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("carousel_slide", {
    url: '/',
    edition: true,
    test:true,
}, () => [
    ...insertSnippet({
        id: 's_carousel',
        name: 'Carousel',
        groupName: "Intro",
    }),
    {
        content: "Select the active carousel item.",
        trigger: ":iframe .carousel-indicators button:nth-child(3)",
        run: "click",
    },
    {
        content: "Check that the carousel has moved to the third slide",
        trigger: ":iframe .carousel-indicators button:nth-child(3).active",
    },
    ...clickOnSave(),
    {
        content: "Ensure that the carousel has moved to the first slide after saving",
        trigger: ":iframe .carousel-indicators",
        run: () => {
            const $carouselIndicators = document.querySelector(':iframe .carousel-indicators');
            if ($carouselIndicators.querySelector('.active').getAttribute('data-slide-to') !== '0') {
                throw new Error('The carousel did not move to the first slide after saving');
            }
        }
    },
]);