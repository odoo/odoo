/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("social_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="social.menu_social_global"]',
            content: markup(_t("Let's create your own <b>social media</b> dashboard.")),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: 'button.o_stream_post_kanban_new_stream',
            content: markup(_t("Let's <b>connect</b> to Facebook, LinkedIn or X.")),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: '.o_social_media_cards',
            content: markup(_t("Choose which <b>account</b> you would like to link first.")),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: 'button.o_stream_post_kanban_new_post',
            content: _t("Let's start posting."),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="message"] .o_input',
            content: _t("Write a message to get a preview of your post."),
            tooltipPosition: 'bottom',
            run: 'edit Awesome post!',
        },
        {
            trigger: 'button[name="action_post"]',
            content: _t("Happy with the result? Let's post it!"),
            tooltipPosition: 'bottom',
            run: "click",
        },
    ],
});
