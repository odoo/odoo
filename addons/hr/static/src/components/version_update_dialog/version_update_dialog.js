import { Component, signal, t, useProps } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dialog } from "@web/core/dialog/dialog";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";

export class VersionUpdateDialog extends Component {
    static template = "hr.VersionUpdateDialog";
    static components = { DateTimeInput, Dialog };

    props = useProps({
        close: t.function(),
        confirm: t.function(),
        info: t.object(),
        record: t.object(),
        changes: t.object(),
        // the previous choice, when the dialog is opened again
        defaultChoice: t.object().optional(),
    });

    choice = signal(this.props.defaultChoice?.mode || this.props.info.selections[0]);
    newVersionDate = signal(
        this.props.info.new_version_date &&
            deserializeDate(this.props.defaultChoice?.date || this.props.info.new_version_date)
    );
    warnings = signal(this.props.info.warnings || []);

    setup() {
        this.orm = useService("orm");
        this.keepLast = new KeepLast();
        if (this.props.defaultChoice) {
            this.updateWarnings();
        }
    }

    getFieldLabel(fieldName) {
        return this.props.record.fields[fieldName]?.string || fieldName;
    }

    getNewVersionDate() {
        return this.choice() === "new_version" ? serializeDate(this.newVersionDate()) : false;
    }

    async updateWarnings() {
        const warnings = await this.keepLast.add(
            this.orm.call("hr.version", "get_version_update_warnings", [
                [this.props.info.version_id],
                this.props.info.version_changes,
                this.choice(),
                this.getNewVersionDate(),
            ])
        );
        this.warnings.set(warnings);
    }

    async onApply() {
        this.props.confirm({
            mode: this.choice(),
            date: this.getNewVersionDate(),
        });
        this.props.close();
    }
}
