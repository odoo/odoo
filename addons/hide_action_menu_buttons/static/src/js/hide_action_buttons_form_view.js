/** @odoo-module **/

import { patch} from "@web/core/utils/patch";
import { FormController } from '@web/views/form/form_controller';
import rpc from 'web.rpc';

patch(FormController.prototype, 'hide_action_menu_buttons.FormController', {
    /**
     * @override
     */

    setup() {

        this._super(...arguments);
        this.isMenu = true
        self = this;
        var domain = [];
        var fields = [];
        rpc.query({
            model: 'hide.action.buttons',
            method: 'check_if_group_view',
            args: [domain, fields],
        }).then(function(result) {

            if (result.models.includes(self.props.resModel) && result.group_hide_action_menu_button_view_form) {
                self.isMenu = false
            };
        })
    },




    getActionMenuItems() {
        this._super()
        const otherActionItems = [];
        if (this.archiveEnabled) {
            if (this.isMenu && this.model.root.isActive) {
                otherActionItems.push({
                    key: "archive",
                    description: this.env._t("Archive"),
                    callback: () => {
                        const dialogProps = {
                            body: this.env._t("Are you sure that you want to archive this record?"),
                            confirmLabel: this.env._t("Archive"),
                            confirm: () => this.model.root.archive(),
                            cancel: () => {},
                        };
                        this.dialogService.add(ConfirmationDialog, dialogProps);
                    },
                });
            } else {
                otherActionItems.push({
                    key: "unarchive",
                    description: this.env._t("Unarchive"),
                    callback: () => this.model.root.unarchive(),
                });
            }
        }
        if (this.isMenu && this.archInfo.activeActions.create && this.archInfo.activeActions.duplicate) {
            otherActionItems.push({
                key: "duplicate",
                description: this.env._t("Duplicate"),
                callback: () => this.duplicateRecord(),
            });
        }
        if (this.isMenu && this.archInfo.activeActions.delete && !this.model.root.isVirtual) {
            otherActionItems.push({
                key: "delete",
                description: this.env._t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            });
        }
        if (!this.isMenu) {
            delete self.props.info.actionMenus.action
        }
        return Object.assign({}, this.props.info.actionMenus, {
            other: otherActionItems
        });
    }
});