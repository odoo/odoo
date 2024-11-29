import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { Component, useRef, useState } from "@odoo/owl";

export class EmailSharingInput extends Component {
    static template = "website_slides.EmailSharingInput";
    static props = {
        id: { type: Number },
        isChannel: { type: Boolean, optional: true },
        isFullscreen: { type: Boolean, optional: true },
        category: { type: String, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.input = useRef("input");
        this.isWebsiteUser = session.is_website_user;
        this.state = useState({
            isDone: false,
            isInvalid: false,
        });
    }

    onKeyPress(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            this.onShareByEmailClick();
        }
    }

    async onShareByEmailClick() {
        const emails = this.input.el.value;
        if (emails) {
            const type = this.props.isChannel ? "channel" : "slide";
            const done = await rpc(`/slides/${type}/send_share_email`, {
                emails: emails,
                fullscreen: this.props.isFullscreen,
                [`${type}_id`]: this.props.id,
            });
            this.state.isDone = done;
            if (done) {
                return;
            }
        }
        this.setInvalid();
    }

    setInvalid() {
        this.state.isInvalid = true;
        this.notification.add(_t("Please enter valid email(s)"), { type: "danger" });
        this.input.el.focus();
    }
}
