/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { GridController } from '@web_grid/views/grid_controller';

export class ConsolidationGridController extends GridController {
    addColumn() {
        this.dialogService.add(
            FormViewDialog, {
                context: { default_period_id: this.props.context.default_period_id },
                title: _t('Add a column'),
                resModel: 'consolidation.journal',
                onRecordSaved: async () => await this.model.fetchData(),
            },
        );
    }
}
