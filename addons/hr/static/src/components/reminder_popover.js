import { Component, t, useProps } from "@odoo/owl";

export class ReminderPopover extends Component {
    static template = "hr.ReminderPopover";

    props = useProps({
        close: t.function(),
        message: t.string(),
        onAction: t.function(),
    });
}
