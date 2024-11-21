/** @odoo-module */

import { _t } from '@web/core/l10n/translation';
import { ConfirmationDialog, deleteConfirmationMessage } from '@web/core/confirmation_dialog/confirmation_dialog';
import { ListRenderer } from '@web/views/list/list_renderer';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';


export class PAVListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async onDeleteRecord(record) {
        const message = await this.orm.call(
            'product.attribute.value',
            'check_is_used_on_products',
            [record.resId],
        )
        if (message) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t("Invalid Operation"),
                body: message,
            });
        }
        if (record.isNew) {
            return super.onDeleteRecord(...arguments);
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Bye-bye, record!"),
            body: deleteConfirmationMessage,
            confirmLabel: _t("Delete"),
            confirm: () => this.onConfirmDelete(record),
            cancel: () => { },
            cancelLabel: _t("No, keep it"),
        });
    }

    async onConfirmDelete(record) {
        await this.orm.unlink('product.attribute.value', [record.resId])
        const res = await super.onDeleteRecord(record);
        await this.props.list.model.root.save();
        return res;
    }
}

export class PAVOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: PAVListRenderer,
    };
}

export const pavOne2ManyField = {
    ...x2ManyField,
    component: PAVOne2ManyField,
}

registry.category("fields").add("pavs_one2many", pavOne2ManyField);
