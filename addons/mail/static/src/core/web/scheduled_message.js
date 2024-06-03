import { Component, useState } from "@odoo/owl";

const { DateTime } = luxon;

/**
 * @typedef {Object} Props
 * @property {import("models").Message} message
 * @extends {Component<Props, Env>}
 */
export class ScheduledMessage extends Component {
    static components = {};
    static props = ["message"];
    static template = "mail.ScheduledMessage";

    setup() {
        super.setup();
        this.state = useState({ showDetails: false });
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }

    get icon() {
        return this.props.message.is_note ? "fa-file-text" : "fa-envelope";
    }

    get recipientsNames() {
        const recipientsNames = this.props.message.recipients.map((recipient) => recipient.name);
        if (!recipientsNames.length) {
            return "";
        }
        return `, ${recipientsNames.join(", ")}`;
    }

    get formattedScheduledDate() {
        return this.props.message.scheduledDatetime.toLocaleString(DateTime.DATETIME_MED);
    }

    get sentIn() {
        return this.props.message.scheduledDatetime
            .diff(DateTime.now())
            .rescale()
            .toHuman()
            .split(",")[0];
    }

    async onClickSendNow() {
        const message_schedule_id = await this.env.services.orm.search("mail.message.schedule", [
            ["mail_message_id", "=", this.props.message.id],
        ]);
        await this.env.services.orm.call("mail.message.schedule", "force_send", [
            message_schedule_id,
        ]);
        const thread = this.props.message.thread;
        this.props.message.delete();
        thread.fetchNewMessages();
    }

    async edit() {
        await this.props.message.editFullComposer();
        this.props.message.thread.fetchMessages();
    }

    async unlink() {
        await this.env.services.orm.unlink("mail.message", [this.props.message.id]);
        this.props.message.delete();
    }
}
