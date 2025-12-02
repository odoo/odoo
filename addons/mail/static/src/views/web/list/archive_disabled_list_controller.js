import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

export class ArchiveDisabledListController extends ListController {
    setup() {
        super.setup();
        this.archiveEnabled = false;
        this.store = useService("mail.store");
    }

    async createRecord() {
        return this.store
            .scheduleActivity(
                this.props.resModel != "mail.activity" ? this.props.resModel : false,
                false
            )
            .then(async () => {
                // Refresh view once new activity has been added
                await this.model.root.load();
            });
    }
}
