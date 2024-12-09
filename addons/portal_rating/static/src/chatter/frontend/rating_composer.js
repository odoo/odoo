import { Composer } from "@mail/core/common/composer";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { RatingComposerDialog } from "./rating_composer_dialog";

import { Component, useEffect, useRef, useState, useSubEnv } from "@odoo/owl";

import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";

export class RatingComposer extends Component {
    static template = "portal_rating.RatingComposer";
    static components = { Composer, OverlayContainer };
    static props = ["defaultMessage?", "defaultRatingValue?", "options", "thread"];

    setup() {
        useSubEnv({
            displayRating: true,
            inPortalRatingComposer: true,
            defaultRatingValue: this.props.defaultRatingValue,
        });
        this.state = useState({
            defaultMessageId: this.props.defaultMessage?.id,
        });
        this.overlayService = useService("overlay");
        this.root = useRef("root");
        this.store = useState(useService("mail.store"));
        useEffect(
            () => {
                const ratingAvg = renderToElement("portal_rating.rating_stars_static", {
                    inline_mode: true,
                    val: this.props.thread.rating_avg || 0,
                });
                $(".o_rating_popup_composer_stars").empty().html(ratingAvg);
            },
            () => [this.props.thread.rating_avg]
        );
    }

    get message() {
        return this.store["mail.message"].get(this.state.defaultMessageId);
    }

    openComposer(ev) {
        if (this.state.defaultMessageId) {
            const text = convertBrToLineBreak(this.message.body);
            this.message.composer = {
                message: this.message,
                text,
                selection: {
                    start: text.length,
                    end: text.length,
                    direction: "none",
                },
                attachments: this.message.attachment_ids,
            };
            this.env.services.dialog.add(RatingComposerDialog, {
                composer: this.message.composer,
                onPostCallback: this.onPostCallback.bind(this),
                thread: this.props.thread,
            },
            { context: this });
        } else {
            this.env.services.dialog.add(RatingComposerDialog, {
                composer: this.props.thread.composer,
                onPostCallback: this.onPostCallback.bind(this),
                thread: this.props.thread,
            },
            { context: this });
        }
    }
    onPostCallback() {
        this.state.defaultMessageId = Object.values(this.store["mail.message"].records).find(
            (msg) => msg.author.id === this.store.self.id
        ).id;
    }
}
