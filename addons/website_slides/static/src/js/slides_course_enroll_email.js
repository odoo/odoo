import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import publicWidget from "@web/legacy/js/public/public_widget";

export const WebsiteSlidesEnroll = publicWidget.Widget.extend({
    selector: "#wrapwrap",
    events: {
        "click .o_wslides_js_channel_enroll": "_onSendRequestClick",
    },
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },
    async _onSendRequestClick(ev) {
        ev.preventDefault();
        const clickedEl = ev.currentTarget;
        const channelId = parseInt(clickedEl.dataset.channelId);
        await new Promise((resolve) =>
            this.call("dialog", "add", ConfirmationDialog, {
                confirm: resolve,
                title: _t("Request Access."),
                body: _t("Do you want to request access to this course?"),
                confirmLabel: _t("Yes"),
                cancel: () => {}, // show cancel button
            })
        );
        const { error, done } = await this.orm.call(
            "slide.channel",
            "action_request_access",
            [channelId],
        );
        const $alert = $(clickedEl.closest(".alert"));
        const message = done ? _t("Request sent!") : error || _t("Unknown error, try again.");
        $alert.replaceWith(`
            <div class="alert alert-${done ? "success" : "danger"}" role="alert">
                <strong>${escape(message)}</strong>
            </div>`);
    },
});

publicWidget.registry.WebsiteSlidesEnroll = WebsiteSlidesEnroll;
