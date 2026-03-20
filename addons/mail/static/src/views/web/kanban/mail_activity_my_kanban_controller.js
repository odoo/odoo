import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";

export class MailActivityMyKanbanController extends KanbanController {
    setup() {
        super.setup();
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
