import { Component, signal, t, useProps } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dialog } from "@web/core/dialog/dialog";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class VersionUpdateDialog extends Component {
    static template = "hr.VersionUpdateDialog";
    static components = { DateTimeInput, Dialog };

    props = useProps({
        close: t.function(),
        confirm: t.function(),
        info: t.object(),
        record: t.object(),
        changes: t.object(),
    });

    choice = signal(this.props.info.selections[0]);
    newVersionDate = signal(
        this.props.info.new_version_date
            ? deserializeDate(this.props.info.new_version_date)
            : DateTime.now().startOf("month")
    );

    getFieldLabel(fieldName) {
        return this.props.record.fields[fieldName]?.string || fieldName;
    }

    async onApply() {
        this.props.confirm({
            mode: this.choice(),
            date: this.choice() === "new_version" ? serializeDate(this.newVersionDate()) : false,
        });
        this.props.close();
    }
}
