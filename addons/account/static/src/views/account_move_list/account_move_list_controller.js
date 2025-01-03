import { _t } from "@web/core/l10n/translation";
import { FileUploadListController } from "../file_upload_list/file_upload_list_controller";
import { AccountFileUploader } from "@account/components/account_file_uploader/account_file_uploader";

import { useService } from "@web/core/utils/hooks";

export class AccountMoveListController extends FileUploadListController {
    static components = {
        ...FileUploadListController.components,
        AccountFileUploader,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.account_move_service = useService("account_move");
        this.showUploadButton = this.props.context.default_move_type !== 'entry' || 'active_id' in this.props.context;
    }

    get actionMenuProps() {
        const actionMenuProps = {
            ...super.actionMenuProps,
<<<<<<< saas-18.1
            printDropdownTitle: _t("Print"),
            loadExtraPrintItems: this.loadExtraPrintItems.bind(this),
||||||| 658711aa1e1809b267006149ed6a547e548c1f90
            printDropdownTitle: _t("Download"),
            loadExtraPrintItems: this.loadExtraPrintItems.bind(this),
=======
            printDropdownTitle: _t("Download"),
>>>>>>> 8f22e52fa9b34ec44e5bdf7016c5d74efa1f38a5
        };
        if (this.props.resModel === "account.move") {
            actionMenuProps.loadExtraPrintItems = this.loadExtraPrintItems.bind(this);
        }
        return actionMenuProps;
    }

    async loadExtraPrintItems() {
        return this.orm.call("account.move", "get_extra_print_items", [this.actionMenuProps.getActiveIds()]);
    }

    async onDeleteSelectedRecords() {
        const selectedResIds = await this.getSelectedResIds();
        if (this.props.resModel !== "account.move" || !await this.account_move_service.addDeletionDialog(this, selectedResIds)) {
            return super.onDeleteSelectedRecords(...arguments);
        }
    }
}
