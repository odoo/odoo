/** @odoo-module **/

import { DataCleaningCommonListController } from "@data_recycle/views/data_cleaning_common_list";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { session } from "@web/session";

export class DataRecycleListController extends DataCleaningCommonListController {
    /**
     * Validate all the records selected
     */
    async onValidateClick() {
        let record_ids;
        if (this.isDomainSelected) {
            const domain = this.props.domain;
            record_ids = await this._domainToResIds(domain, session.active_ids_limit);
        } else {
            record_ids = await this.getSelectedResIds();
        }

        await this.orm.call('data_recycle.record', 'action_validate', [record_ids]);
        await this.model.load();
        this.model.notify();
    }
};

registry.category('views').add('data_recycle_list', {
    ...listView,
    Controller: DataRecycleListController,
    buttonTemplate: 'DataRecycle.buttons',
});

