/** @odoo-module **/

import { DataCleaningCommonListController } from "@data_recycle/views/data_cleaning_common_list";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class DataCleaningListController extends DataCleaningCommonListController {
    /**
     * Validate all the records selected
     */
    async onValidateClick() {
        const record_ids = await this.getSelectedResIds();
        await this.orm.call('data_cleaning.record', 'action_validate', [record_ids]);
        await this.model.load();
    }
}

registry.category('views').add('data_cleaning_list', {
    ...listView,
    Controller: DataCleaningListController,
    buttonTemplate: 'DataCleaning.buttons',
});

