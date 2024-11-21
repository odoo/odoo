import { MailComposerScheduleDialog } from "@mail/chatter/web/mail_composer_schedule_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

class MailComposerSendDropdown extends Component {
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = standardWidgetProps;
    static template = "mail.MailComposerSendDropdown";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }

    async onClickSend() {
        // don't send message if save failed (eg. missing required field )
        if (await this.props.record.save()) {
            // schedule the message if a scheduled_date is set on the composer
            // (when using a template with a scheduled_date on it)
            const method = this.props.record.data.scheduled_date
                ? "action_schedule_message"
                : "action_send_mail";
            this.actionService.doAction(
                await this.orm.call("mail.compose.message", method, [this.props.record.resId], {
                    context: this.props.record.context,
                }),
            );
        }
    }

    async onClickSendLater() {
        // don't open dialog if save failed (eg. missing required field)
        if (await this.props.record.save()) {
            this.dialogService.add(MailComposerScheduleDialog, {
                isNote: this.props.record.data.subtype_is_log,
                schedule: async (scheduledDate) => {
                    await this.env.services.action.doAction(
                        await this.env.services.orm.call(
                            "mail.compose.message",
                            "action_schedule_message",
                            [this.props.record.resId, scheduledDate],
                            { context: this.props.record.context },
                        ),
                    );
                },
            });
        }
    }
}

const mailComposerSendDropdown = { component: MailComposerSendDropdown };

registry.category("view_widgets").add("mail_composer_send_dropdown", mailComposerSendDropdown);
