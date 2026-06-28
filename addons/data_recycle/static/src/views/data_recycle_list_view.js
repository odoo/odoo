import { useLayoutEffect } from "@web/owl2/utils";
import { DataCleaningCommonListController } from "@data_recycle/views/data_cleaning_common_list";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class DataRecycleListController extends DataCleaningCommonListController {
    setup() {
        super.setup();
        useLayoutEffect(() => {
            const selectedRecords = this.model.root.selection;

            // Check the active state of selected records
            const allInactive = selectedRecords.every(r => r.data.active === false);
            const allActive = selectedRecords.every(r => r.data.active === true);

            // Helper function to toggle the 'd-none' class
            const toggleBtnVisibility = (selector, shouldShow) => {
                const btn = document.querySelector(selector);
                if (btn) btn.classList.toggle('d-none', !shouldShow);
            };

            toggleBtnVisibility('button[name="action_validate"]', allActive);
            toggleBtnVisibility('button[name="action_discard"]', allActive);
            toggleBtnVisibility('button[name="action_undiscard"]', allInactive);
        });
    }
};

registry.category('views').add('data_recycle_list', {
    ...listView,
    Controller: DataRecycleListController,
});

