import { ListController } from "@web/views/list/list_controller";

export class ArchiveDisabledListController extends ListController {
    setup() {
        super.setup();
        this.archiveEnabled = false;
    }
}
