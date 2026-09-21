import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("edit_contact_field", {
    url: "/my/home",
    edition: true,
}, () => [
    {
        content: "Click on the email icon of the contact field",
        trigger: ":iframe [data-oe-type='contact'] i.fa-envelope",
        run: "click",
    },
    {
        content: "Check that the contact can be changed but the icon cannot be customized",
        trigger: ".o_we_customize_panel:has(.snippet-option-many2one):not(:has(.snippet-option-FontawesomeTools, .snippet-option-ReplaceMedia))",
    },
]);
