/* @odoo-module */

import { PortalChatterService } from "@portal/chatter/frontend/portal_chatter_service";
import { RatingComposer } from "@portal_rating/chatter/frontend/rating_composer";

import { App } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";
import { patch } from "@web/core/utils/patch";

patch(PortalChatterService.prototype, {
    async initialize(env) {
        super.initialize(...arguments);
        const ratingComposerEl = document.querySelector(".o_rating_popup_composer");
        if (ratingComposerEl) {
            const props = {
                message: {
                    res_id: parseInt(ratingComposerEl.getAttribute("data-res_id")),
                    model: ratingComposerEl.getAttribute("data-res_model"),
                    id: parseInt(ratingComposerEl.getAttribute("data-default_message_id")),
                    body: ratingComposerEl.getAttribute("data-default_message"),
                    rating_value: parseInt(
                        ratingComposerEl.getAttribute("data-default_rating_value")
                    ),
                    rating_avg: ratingComposerEl.getAttribute("data-rating_avg")
                        ? parseFloat(ratingComposerEl.getAttribute("data-rating_avg"))
                        : 0,
                    attachments: JSON.parse(
                        ratingComposerEl.getAttribute("data-default_attachment_ids")
                    ),
                },
                options: {
                    linkBtnClasses: ratingComposerEl.getAttribute("data-link_btn_classes"),
                    textClasses: ratingComposerEl.getAttribute("data-text_classes"),
                    fullScreen: ratingComposerEl.getAttribute("data-is_fullscreen"),
                    displayComposer: ratingComposerEl.getAttribute("data-display_composer"),
                    icon: ratingComposerEl.getAttribute("data-icon"),
                    hideRatingAvg: ratingComposerEl.getAttribute("data-hide_rating_avg"),
                },
                portalSecurity: {
                    token: ratingComposerEl.getAttribute("data-token"),
                    hash: ratingComposerEl.getAttribute("data-hash"),
                    pid: parseInt(ratingComposerEl.getAttribute("data-pid")),
                },
            };
            const root = document.createElement("div");
            root.setAttribute("id", "ratingComposerRoot");
            ratingComposerEl.appendChild(root);
            this.createShadow(root).then((shadow) => {
                new App(RatingComposer, {
                    env,
                    getTemplate,
                    props,
                    translatableAttributes: ["data-tooltip"],
                    translateFn: _t,
                    dev: env.debug,
                }).mount(shadow);
            });
            if (this.store.self.id === -1) {
                this.setUser(ratingComposerEl);
            }
        }
    },
});
