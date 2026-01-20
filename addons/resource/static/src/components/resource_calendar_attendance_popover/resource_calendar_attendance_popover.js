import { Record } from "@web/model/record";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Component, useRef } from "@odoo/owl";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ResourceCalendarAttendancePopover extends Component {
    static template = "resource.ResourceCalendarAttendancePopover";
    static components = {
        Record,
        FormRenderer,
        ViewButton,
    };
    static props = {
        close: Function,
        onReload: Function,
        originalRecord: { type: Object, optional: true },
        recordProps: { type: Object },
        archInfo: { type: Object },
        context: { type: Object },
    };
    static additionalFieldsToFetch = [
        { name: "calendar_id", type: "many2one", readonly: false },
        { name: "display_name", type: "char", readonly: false },
        { name: "date", type: "date", readonly: false },
        { name: "duration_based", type: "boolean", readonly: false },
    ];

    setup() {
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        useViewButtons(this.rootRef, {
            reload: this.props.onReload,
            afterExecuteAction: this.props.close,
        });
    }

    get currentRecordProps() {
        return {
            ...this.props.recordProps,
            resId: this.props.originalRecord?.id,
            mode: "edit",
            context: this.props.context,
        };
    }

    async onSave(currentRecord) {
        await executeButtonCallback(this.rootRef.el, async () => {
            if (await currentRecord.checkValidity()) {
                try {
                    await currentRecord.save();
                    await this.props.onReload();
                    this.props.close();
                } catch (error) {
                    return this.notification.add(_t(error.data.message), { type: "danger" });
                }
            }
        });
    }
}
