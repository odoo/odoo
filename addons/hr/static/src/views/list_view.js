import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';

export class EmployeeListController extends ListController {}

registry.category('views').add('hr_employee_list', {
    ...listView,
    Controller: EmployeeListController,
});
