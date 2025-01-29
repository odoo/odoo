import { PortalChatterService } from "@portal/chatter/frontend/portal_chatter_service";
import { RatingComposer } from "@portal_rating/chatter/frontend/rating_composer";

import { App } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";
import { patch } from "@web/core/utils/patch";

const chatterServicePatch = {
    async initialize(env) {
        await super.initialize(...arguments);
        const ratingComposerEl = document.querySelector(".o_rating_popup_composer");
        if (!ratingComposerEl) {
            return;
        }
        const props = {
            options: {
                linkBtnClasses: ratingComposerEl.getAttribute("data-link_btn_classes"),
                textClasses: ratingComposerEl.getAttribute("data-text_classes"),
                fullScreen: ratingComposerEl.getAttribute("data-is_fullscreen"),
                displayComposer: ratingComposerEl.getAttribute("data-display_composer"),
                allowVoidContent: ratingComposerEl.getAttribute("data-rate_with_void_content"),
                icon: ratingComposerEl.getAttribute("data-icon"),
                hideRatingAvg: ratingComposerEl.getAttribute("data-hide_rating_avg"),
            },
            thread: this.store.Thread.insert({
                model: ratingComposerEl.getAttribute("data-res_model"),
                id: parseInt(ratingComposerEl.getAttribute("data-res_id")),
            }),
        };
        const defaultMessageId = parseInt(ratingComposerEl.getAttribute("data-default_message_id"));
        if (defaultMessageId) {
            props.defaultMessage = this.store["mail.message"].insert({
                id: parseInt(ratingComposerEl.getAttribute("data-default_message_id")),
                author: this.store.self,
                body: ratingComposerEl.getAttribute("data-default_message"),
                attachment_ids: JSON.parse(
                    ratingComposerEl.getAttribute("data-default_attachment_ids")
                ),
                model: props.thread.model,
                res_id: props.thread.id,
                thread: props.thread,
            });
            props.defaultRatingValue = parseInt(
                ratingComposerEl.getAttribute("data-default_rating_value")
            );
        }
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
            await this.initChatter(props.thread.model, props.thread.id, {
                token: ratingComposerEl.getAttribute("data-token"),
                hash: ratingComposerEl.getAttribute("data-hash"),
                pid: parseInt(ratingComposerEl.getAttribute("data-pid")),
            });
        }
    },
};
patch(PortalChatterService.prototype, chatterServicePatch);
