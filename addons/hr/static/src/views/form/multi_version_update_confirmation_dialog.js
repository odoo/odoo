import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { smartDateUnits } from "@web/core/l10n/dates";
import { useAutofocus } from "@web/core/utils/hooks";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { Operation } from "@web/model/relational_model/operation";
import { Field, fieldVisualFeedback } from "@web/views/fields/field";
import { formatDate } from "@web/views/fields/formatters";

import { Component, props, t } from "@odoo/owl";
const { DateTime } = luxon;

export class MultiVersionUpdateConfirmationDialog extends Component {
    static template = "hr.FormView.MultiVersionUpdateConfirmation";
    static components = { BadgeTag, Dialog, Field };
    props = props({
        close: t.function(),
        title: t.string().optional(_t("Confirmation")),
        confirm: t.function().optional(),
        cancel: t.function().optional(),
        isDomainSelected: t.boolean().optional(),
        fields: t.array().optional(),
        nbRecords: t.number().optional(),
        nbValidRecords: t.number().optional(),
        record: t.object().optional(),
        changes: t.object().optional(),
    });

    setup() {
        useAutofocus();
    }

    get updateConfirmationText() {
        return _t("You are going to apply the following changes to the %(version)s version, do you also want to apply them to all following versions?", {
            version: 'a',
        });
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
