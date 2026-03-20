import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { smartDateUnits } from "@web/core/l10n/dates";
import { useAutofocus } from "@web/core/utils/hooks";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { Operation } from "@web/model/relational_model/operation";
import { Field, fieldVisualFeedback } from "@web/views/fields/field";
import { formatDate } from "@web/views/fields/formatters";

import { Component } from "@odoo/owl";
const { DateTime } = luxon;

export class ListConfirmationDialog extends Component {
    static template = "web.ListView.ConfirmationModal";
    static components = { BadgeTag, Dialog, Field };
    static props = {
        close: Function,
        title: {
            validate: (m) =>
                typeof m === "string" ||
                (typeof m === "object" && typeof m.toString === "function"),
            optional: true,
        },
        confirm: { type: Function, optional: true },
        cancel: { type: Function, optional: true },
        isDomainSelected: Boolean,
        fields: Object,
        nbRecords: Number,
        nbValidRecords: Number,
        record: Object,
        changes: Object,
    };
    static defaultProps = {
        title: _t("Confirmation"),
    };

    setup() {
        useAutofocus();
    }

    get dateTip() {
        const invertedSmartDateUnits = Object.create(null);
        for (const [k, v] of Object.entries(smartDateUnits)) {
            invertedSmartDateUnits[v] = k;
        }
        return _t(
            `Use the operators "+=", "-=" to update the current date by days (%(days)s), 
            weeks (%(weeks)s), months (%(months)s), years (%(years)s), hours (%(hours)s), 
            minutes (%(minutes)s) and seconds (%(seconds)s).`,
            invertedSmartDateUnits
        );
    }

    get dateTipExample() {
        return _t(
            `For example, if the date is %(today)s and you enter "+=2d", 
            it will be updated to %(future)s.`,
            {
                today: formatDate(DateTime.now()),
                future: formatDate(DateTime.now().plus({ days: 2 })),
            }
        );
    }

    get showDateTip() {
        return this.props.fields.some((field) =>
            ["date", "datetime"].includes(field.fieldNode?.type)
        );
    }

    get showNumberTip() {
        return this.props.fields.some((field) =>
            ["monetary", "integer", "float"].includes(field.fieldNode?.type)
        );
    }

    get showTip() {
        return this.showDateTip || this.showNumberTip;
    }

    get updateConfirmationText() {
        return _t("Are you sure you want to update %(count)s records?", {
            count: this.props.nbValidRecords,
        });
    }

    get validRecordsText() {
        return _t(
            "Among the %(total)s selected records, %(valid_count)s are valid for this update.",
            {
                total: this.props.nbRecords,
                valid_count: this.props.nbValidRecords,
            }
        );
    }

    _cancel() {
        if (this.props.cancel) {
            this.props.cancel();
        }
        this.props.close();
    }

    async _confirm() {
        if (this.props.confirm) {
            await this.props.confirm();
        }
        this.props.close();
    }

    getTagProps(records, field) {
        const colorField = field.fieldNode.options?.color_field;
        return records.map((record) => ({
            id: record.id,
            text: record.data.display_name,
            color: colorField ? record.data[colorField] : undefined,
        }));
    }

    isValueEmpty(field) {
        const fieldNode = field.fieldNode || {};
        return fieldVisualFeedback(fieldNode.field || {}, this.props.record, field.name, {
            ...fieldNode,
            // force readonly as we force that state on the Field component
            readonly: true,
        }).empty;
    }

    isValueOperation(field) {
        return this.props.changes[field.name] instanceof Operation;
    }
}
