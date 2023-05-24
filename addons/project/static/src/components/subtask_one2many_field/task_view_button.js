/** @odoo-module */

import { ViewButton } from "@web/views/view_button/view_button";
import { useService } from "@web/core/utils/hooks";

export class TaskViewButton extends ViewButton {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }
    async onClick(ev) {
        const record = this.props.record;
        if (this.props.clickParams.name != "action_open_task") {
            return super.onClick(ev);
        }
        if (await this.props.record.checkValidity() && await this.props.record.model.root.checkValidity()) {
            await record.save({ noReload: true })
            const action = await this.orm.call(
                record.resModel,
                "action_open_task",
                [record.resId],
            );
            this.actionService.doAction(action);
        } else {
            this.props.record.openInvalidFieldsNotification();
            this.props.record.model.root.openInvalidFieldsNotification();
        }
    }
}
