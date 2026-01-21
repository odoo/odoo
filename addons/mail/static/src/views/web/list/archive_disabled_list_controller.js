import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

export class ArchiveDisabledListController extends ListController {
    setup() {
        super.setup();
        this.archiveEnabled = false;
        this.store = useService("mail.store");
    }

    get deleteConfirmationDialogProps() {
        return {
            title: _t("Delete Activities"),
            body: _t(
                "Are you sure you want to delete these activities? It will be gone forever!\nThink twice before you click that 'Delete' button!"
            ),
            confirmLabel: _t("Yes, delete"),
            cancelLabel: _t("No, go back"),
        };
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
