import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

/* todo guce:
 * Should this component be renamed?
 * The logic for activity creation without a record set has been applied here because it was useful in the same places
 * that not showing an archival option made sense, but the component is misnommed as a result.
 */
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
