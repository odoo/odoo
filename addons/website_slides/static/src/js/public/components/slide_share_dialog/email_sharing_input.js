import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { Component, proxy, signal, t, useProps } from "@odoo/owl";

export class EmailSharingInput extends Component {
    static template = "website_slides.EmailSharingInput";
    props = useProps({
        id: t.number(),
        isChannel: t.boolean().optional(),
        isFullscreen: t.boolean().optional(),
        category: t.string().optional(),
    });

    inputRef = signal.ref();

    setup() {
        this.notification = useService("notification");
        this.isWebsiteUser = session.is_website_user;
        this.state = proxy({
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
        const emails = this.inputRef()?.value;
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
        this.inputRef()?.focus();
    }
}
