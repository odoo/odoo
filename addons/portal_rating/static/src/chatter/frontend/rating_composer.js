/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { Component, useSubEnv, useState, onWillStart } from "@odoo/owl";

import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { renderToElement } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

export class RatingComposer extends Component {
    static template = "portal_rating.ratingComposer";
    static components = { Composer, OverlayContainer };
    static props = ["displayRating", "portalSecurity", "options", "message"];

    setup() {
        useSubEnv({
            shadowRootId: "ratingComposerRoot",
            displayRating: true,
            portalSecurity: this.props.portalSecurity,
            ratingOptions: { ...this.props.options, messageId: this.props.message.id },
        });
        this.state = useState({
            defaultMessageId: this.props.message.id,
        });
        this.overlayService = useService("overlay");
        this.store = useState(useService("mail.store"));
        this.popover = usePopover(Composer, {
            position: "top",
            popoverClass: "d-flex align-items-center justify-content-center",
        });
        onWillStart(() => {
            const ratingAvg = renderToElement("portal_rating.rating_stars_static", {
                inline_mode: true,
                val: this.message.rating_avg,
            });
            $(".o_rating_popup_composer_stars").empty().html(ratingAvg);
        });
    }

    get thread() {
        return this.store.Thread.insert({
            model: this.props.message.model,
            id: this.props.message.res_id,
        });
    }
    get message() {
        if (this.state.defaultMessageId && this.store.Message.get(this.state.defaultMessageId)) {
            return this.store.Message.get(this.state.defaultMessageId);
        }
        return this.store.Message.insert(this.props.message);
    }

    openComposer(ev) {
        if (this.popover.isOpen) {
            return this.popover.close();
        }
        if (this.state.defaultMessageId) {
            this.message.composer = {
                message: this.message,
                text: convertBrToLineBreak(this.message?.body),
                selection: {
                    start: convertBrToLineBreak(this.message?.body).length,
                    end: convertBrToLineBreak(this.message?.body).length,
                    direction: "none",
                },
                attachments: this.message.attachments,
            };
            this.popover.open(ev.target, {
                composer: this.message.composer,
                onPostCallback: this.onPostCallback.bind(this),
            });
        } else {
            this.popover.open(ev.target, {
                composer: this.thread.composer,
                onPostCallback: this.onPostCallback.bind(this),
            });
        }
    }
    onPostCallback() {
        if (!this.state.defaultMessageId) {
            this.state.defaultMessageId = this.thread.messages.find(
                (msg) => msg.author.id === this.store.self.id
            ).id;
            this.env.ratingOptions.messageId = this.state.defaultMessageId;
        }
        if (
            !this.props.options.hideRatingAvg &&
            this.props.message.rating_avg !== this.message.rating_avg
        ) {
            const ratingAvg = renderToElement("portal_rating.rating_stars_static", {
                inline_mode: true,
                val: this.message.rating_avg,
            });
            $(".o_rating_popup_composer_stars").empty().html(ratingAvg);
        }
        if (this.props.message.rating_count !== this.message.rating_count) {
            const reviewEl = document.querySelector("#review-tab");
            if (reviewEl) {
                reviewEl.textContent = _t("Reviews (%s)", this.message.rating_count);
            }
        }
        this.popover.close();
    }
}
