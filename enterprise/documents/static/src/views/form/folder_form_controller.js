/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { preSuperSetupFolder } from "@documents/views/hooks";

export class FolderFormController extends FormController {
    setup() {
        preSuperSetupFolder();
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    }

    /**
     * @override
     */
    getStaticActionMenuItems() {
        const { activeActions } = this.archInfo;
        return {
            duplicate: {
                isAvailable: () => activeActions.create && activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecord(),
            },
            unarchive: {
                isAvailable: () => !this.model.root.data.active,
                sequence: 20,
                icon: "fa fa-history",
                description: _t("Restore"),
                callback: () => this.model.root.unarchive(),
            },
            delete: {
                isAvailable: () =>
                    activeActions.delete && !this.model.root.isNew && this.model.root.data.active,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            },
        };
    }

    /**
     * @override
     */
    async deleteRecord() {
        const displayDialog = await this.orm.call(
            this.props.resModel,
            "is_folder_containing_document",
            [this.model.root.resId]
        );
        if (displayDialog) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Move to trash?"),
                body: _t(
                    "Files will be sent to trash and deleted forever after %s days.",
                    this._deletionDelay
                ),
                confirmLabel: _t("Move to trash"),
                confirm: async () => {
                    await this.orm.call(
                        this.props.resModel,
                        "action_archive",
                        [this.model.root.resId]
                    );
                    this.env.config.historyBack();
                },
                cancel: () => {},
            });
        } else {
            await this.orm.call(this.props.resModel, "action_archive", [this.model.root.resId]);
            this.env.config.historyBack();
        }
    }
}
