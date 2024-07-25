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
        return {
            ...super.actionMenuProps,
            printDropdownTitle: _t("Download"),
            loadExtraPrintItems: this.loadExtraPrintItems.bind(this),
        };
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
