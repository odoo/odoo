import { onMounted, onPatched } from "@odoo/owl";
import { DataCleaningCommonListController } from "@data_recycle/views/data_cleaning_common_list";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class DataRecycleListController extends DataCleaningCommonListController {
    setup() {
        super.setup();
        const syncButtonVisibility = () => {
            const selectedRecords = this.model.root.selection;
            const allInactive = selectedRecords.every(r => r.data.active === false);
            const allActive = selectedRecords.every(r => r.data.active === true);
            const toggleBtnVisibility = (selector, shouldShow) => {
                const btn = document.querySelector(selector);
                if (btn) btn.classList.toggle('d-none', !shouldShow);
            };
            toggleBtnVisibility('button[name="action_validate"]', allActive);
            toggleBtnVisibility('button[name="action_discard"]', allActive);
            toggleBtnVisibility('button[name="action_undiscard"]', allInactive);
        };
        onMounted(syncButtonVisibility);
        onPatched(syncButtonVisibility);
    }
};

registry.category('views').add('data_recycle_list', {
    ...listView,
    Controller: DataRecycleListController,
});

