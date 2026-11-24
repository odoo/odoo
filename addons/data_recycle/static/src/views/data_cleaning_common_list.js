import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";


export class DataCleaningCommonListController extends ListController {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    }
};
