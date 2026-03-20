import { ListController } from '@web/views/list/list_controller';

export class ProjectUpdateListController extends ListController {
    get className() {
        return super.className + ' o_updates_controller';
    }
}
