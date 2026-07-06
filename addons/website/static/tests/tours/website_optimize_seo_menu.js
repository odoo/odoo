import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website.test_website_seo_with_duplicate_images_across_html_fields",
    { url: "/optimize_seo_test_page" },
    () => [
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
        {
            content: "check that the image from s_banner has been loaded in the modal",
            trigger:
                ".oe_seo_configuration .o_seo_images_check img[src='/web/image/website.s_banner_default_image']",
        },
    ]
);
