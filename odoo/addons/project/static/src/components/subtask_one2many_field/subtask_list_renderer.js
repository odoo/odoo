/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ListRenderer } from '@web/views/list/list_renderer';

import { useEffect } from "@odoo/owl";

export class SubtaskListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        useEffect(
            (editedRecord) => this.focusName(editedRecord),
            () => [this.editedRecord]
        );
    }

    focusName(editedRecord) {
        if (editedRecord?.isNew && !editedRecord.dirty) {
            const col = this.state.columns.find((c) => c.name === "name");
            this.focusCell(col);
        }
    }

    async onDeleteRecord(record) {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this record?"),
            confirm: () => super.onDeleteRecord(record),
            cancel: () => {},
        });
    }
}
