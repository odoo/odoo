import { onWillStart } from "@odoo/owl";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { referenceField, ReferenceField } from "@web/views/fields/reference/reference_field";

class MailPreviewRecordField extends ReferenceField {
    static components = {
        ...super.components,
        Pager,
    };
    static template = "mail.MailPreviewRecordField";

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");

        if (this.currentResId) {
            onWillStart(async () => {
                this.records = [
                    {
                        id: this.currentResId,
                        display_name: this.props.record.data[this.props.name].display_name,
                    },
                ];
                // Load other records to enable navigation
                const loadedRecords = await this.orm.searchRead(
                    this.props.record.data[this.props.name].resModel,
                    [["id", "!=", this.currentResId]],
                    ["id", "display_name"],
                    { limit: 9 }
                );
                this.records.push(
                    ...loadedRecords.map((r) => ({ id: r.id, display_name: r.display_name }))
                );
            });
        }
    }

    get currentResId() {
        return this.props.record.data[this.props.name]?.resId || false;
    }

    setCurrentResId(value) {
        return this.props.record.update({
            [this.props.name]: {
                displayName: value.display_name,
                resId: value.id,
                resModel: this.props.record.data[this.props.name].resModel,
            },
        });
    }

    get pagerProps() {
        return {
            isEditable: false,
            limit: 1,
            offset: this.records.findIndex((record) => record.id === this.currentResId),
            total: this.records.length || 0,
            onUpdate: async ({ offset }) => {
                await this.setCurrentResId(this.records[offset]);
            },
        };
    }
}

export const mailPreviewRecordField = {
    ...referenceField,
    component: MailPreviewRecordField,
};

registry.category("fields").add("mail_preview_record_field", mailPreviewRecordField);
