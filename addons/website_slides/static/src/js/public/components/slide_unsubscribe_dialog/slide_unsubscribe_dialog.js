/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class SlideUnsubscribeDialog extends Component {
    static template = "website_slides.SlideUnsubscribeDialog";
    static components = { CheckBox, Dialog };
    static props = {
        channelId: Number,
        isFollower: { type: String, optional: true },
        visibility: String,
        enroll: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.state = useState({
            buttonDisabled: false,
        });
        this.channelID = parseInt(this.props.channelId, 10);
        this.isFollower = this.props.isFollower === "True";
        this.updateState("subscription");
        this.isChecked = this.isFollower;
    }

    updateState(mode) {
        if (mode === "subscription") {
            this.state.title = this.isFollower ? _t("Subscribe") : _t("Notifications");
            this.state.mode = "subscription";
        } else if (mode === "leave") {
            this.state.title = _t("Leave the course");
            this.state.mode = "leave";
        }
    }

    onChangeCheckbox(isChecked) {
        this.isChecked = isChecked;
    }

    onClickLeaveCourse() {
        this.updateState("leave");
    }

    onClickLeaveCourseCancel() {
        this.updateState("subscription");
    }

    async onClickLeaveCourseSubmit() {
        if (this.state.buttonDisabled) {
            return;
        }
        this.state.buttonDisabled = true;

        await rpc("/slides/channel/leave", { channel_id: this.channelID });
        if (this.props.visibility === "public" || this.props.visibility === "connected") {
            window.location.reload();
        } else {
            window.location.href = "/slides";
        }
    }

    async onClickSubscriptionSubmit() {
        if (this.state.buttonDisabled) {
            return;
        }
        this.state.buttonDisabled = true;

        if (this.isFollower === this.isChecked) {
            this.props.close();
        } else {
            await rpc(`/slides/channel/${this.isChecked ? "subscribe" : "unsubscribe"}`, {
                channel_id: this.channelID,
            });
            window.location.reload();
        }
    }
}
