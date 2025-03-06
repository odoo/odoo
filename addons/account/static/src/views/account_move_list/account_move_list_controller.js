import { _t } from "@web/core/l10n/translation";
import { FileUploadListController } from "../file_upload_list/file_upload_list_controller";
import { AccountFileUploader } from "@account/components/account_file_uploader/account_file_uploader";
import { deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";

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
            printDropdownTitle: _t("Print"),
            loadExtraPrintItems: this.loadExtraPrintItems.bind(this),
        };
    }

    async loadExtraPrintItems() {
        return this.orm.call("account.move", "get_extra_print_items", [this.actionMenuProps.getActiveIds()]);
    }

    async onDeleteSelectedRecords() {
        const deleteConfirmationDialogProps = this.deleteConfirmationDialogProps;
        const selectedResIds = await this.model.root.getResIds(true);
        if (this.props.resModel === "account.move") {
            let body = deleteConfirmationMessage;
            if (this.model.root.isDomainSelected || this.model.root.selection.length > 1) {
                body = _t("Are you sure you want to delete these records?");
            }
            deleteConfirmationDialogProps.body = await this.account_move_service.getDeletionDialogBody(body, selectedResIds);
        }
        this.deleteRecordsWithConfirmation(
            deleteConfirmationDialogProps
        );
    }
}
