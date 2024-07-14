/** @odoo-module **/

import { Field } from "@web/views/fields/field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { _t } from "@web/core/l10n/translation";

export class DocumentsInspectorField extends Field {
    get fieldComponentProps() {
        const doLockAction = this.props.lockAction;
        const record = this.props.record;
        const props = super.fieldComponentProps;

        // Set "Multiple Values" instead of the actual value in case multiple values are selected for
        //  Many2one Fields.
        if (
            this.field.component === Many2OneField &&
            new Set(
                this.props.documents.map((rec) => (rec.data[this.props.name] ? rec.data[this.props.name][0] : false))
            ).size > 1
        ) {
            props.value = [null, _t("Multiple values")];
        }

        props.readonly = this.props.inspectorReadonly || false;

        if (!record.isDocumentsInspector) {
            record.isDocumentsInspector = true;
            const recordUpdate = record.update.bind(record);
            record.update = async (value) => {
                if (record.model.multiEdit && record.selected) {
                    if (!record.isInEdition) {
                        record.model.root.enterEditMode(record);
                    }
                }
                doLockAction(async () => {
                    await recordUpdate(value);

                    if (!record.selected) {
                        // need to save manually after the update, otherwise if the record
                        // is not selected, the change won't be applied
                        await record.save();
                    }
                });
            };
        }

        delete props.documents;
        delete props.inspectorReadonly;
        delete props.lockAction;
        return props;
    }
}
