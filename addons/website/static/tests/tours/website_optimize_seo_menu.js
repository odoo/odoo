import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

const openSeoModalSteps = [
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
];

registerWebsitePreviewTour(
    "website.test_website_seo_with_duplicate_images_across_html_fields",
    { url: "/optimize_seo_test_page" },
    () => [
        ...openSeoModalSteps,
        {
            content: "check if the Optimize SEO modal is successfully triggered",
            trigger: ".oe_seo_configuration",
        },
        {
            content: "check that the image from s_banner has been loaded in the modal",
            trigger:
                ".oe_seo_configuration .o_seo_images_check img[src='/web/image/website.s_banner_default_image']",
        },
        {
            content: "Add an alt to one of the images",
            trigger: ".oe_seo_configuration .o_seo_images_check input.form-control.is-invalid",
            run: "edit A very good description",
        },
        {
            content: "Save the changes",
            trigger: ".modal-footer button:contains('Save')",
            run: "click",
        },
        {
            content:
                "Wait for the iframe to load and check that the image's alt was properly edited",
            trigger:
                ":iframe [is-ready=true] #wrapwrap:has(#zone_left img[alt='A very good description'])",
        },
        ...openSeoModalSteps,
        {
            content: "Check the modifications are still present in the modal",
            trigger: ".oe_seo_configuration .o_seo_images_check input.form-control.is-valid",
            run: () => {
                const input = document.querySelector(
                    ".oe_seo_configuration .o_seo_images_check input.form-control.is-valid"
                );
                if (input.value !== "A very good description") {
                    throw new Error("The input should have the image's alt as a value");
                }
            },
        },
    ]
);
