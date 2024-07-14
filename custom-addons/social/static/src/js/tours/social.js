/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('social_tour', {
        url: "/web",
        rainbowManMessage: () => markup(_t(`<strong>Congrats! Come back in a few minutes to check your statistics.</strong>`)),
        sequence: 190,
        steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="social.menu_social_global"]',
            content: markup(_t("Let's create your own <b>social media</b> dashboard.")),
            position: 'bottom',
            edition: 'enterprise',
        }, {
            trigger: 'button.o_stream_post_kanban_new_stream',
            content: markup(_t("Let's <b>connect</b> to Facebook, LinkedIn or Twitter.")),
            position: 'bottom',
            edition: 'enterprise',
        }, {
            trigger: '.o_social_media_cards',
            content: markup(_t("Choose which <b>account</b> you would like to link first.")),
            position: 'right',
            edition: 'enterprise',
        }, {
            trigger: 'button.o_stream_post_kanban_new_post',
            content: _t("Let's start posting."),
            position: 'bottom',
            edition: 'enterprise',
        }, {
            trigger: '.o_social_post_message_wrapper',
            content: _t("Write a message to get a preview of your post."),
            position: 'bottom',
            edition: 'enterprise',
        }, {
            trigger: 'button[name="action_post"]',
            extra_trigger: 'textarea[name="message"]:first:propValueContains()', // message field not empty
            content: _t("Happy with the result? Let's post it!"),
            position: 'bottom',
            edition: 'enterprise',
        },
    ]
});
