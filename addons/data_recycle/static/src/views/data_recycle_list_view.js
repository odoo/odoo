import { DataCleaningCommonListController } from "@data_recycle/views/data_cleaning_common_list";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class DataRecycleListController extends DataCleaningCommonListController {};

registry.category('views').add('data_recycle_list', {
    ...listView,
    Controller: DataRecycleListController,
});

