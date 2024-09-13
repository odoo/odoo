import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("mailing_editor_images", {
    url: "/odoo",
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: ".o_app[data-menu-xmlid='mass_mailing.mass_mailing_menu_root']",
    run: "click",
}, {
    trigger: "button.o_list_button_add",
    run: "click",
}, {
    content: "Click on the 'Event Promo' template",
    trigger: "[name='body_arch'] :iframe a#event",
    run: "click",
}, {
    content: "Wait for the template to be rendered",
    trigger: "[name='body_arch'] :iframe .s_header_social",
}, {
    content: "Add a subject to the mail",
    trigger: "input#subject_0",
    run: "edit TestFromTour",
}, {
    content: "Click on first image of the template",
    trigger: "[name='body_arch'] :iframe [data-snippet='s_media_list'] [data-name='Media item']:contains('Get 6-months') img",
    run: "click",
}, {
    content: "Click on the filter option",
    trigger: "we-select:contains('Filter') we-toggler:contains('None')",
    run: "click",
}, {
    content: "Add a Blur filter on the image",
    trigger: "[data-gl-filter='blur']",
    run: "click",
}, {
    content: "Ensure that the image has been modified",
    trigger: "[name='body_arch'] :iframe [data-snippet='s_media_list'] img.o_modified_image_to_save",
}, {
    content: "Click on Save",
    trigger: "button.o_form_button_save",
    run: "click",
}, {
    content: "Ensure that the image has been saved",
    trigger: "[name='body_arch'] :iframe [data-snippet='s_media_list'] [data-name='Media item']:contains('Get 6-months') img:not(.o_modified_image_to_save)",
},
]});
