/** @odoo-module */
/**
 * This file will used to hide the selected options from the list view
 */
import { ListController} from '@web/views/list/list_controller';
import { patch} from "@web/core/utils/patch";
var rpc = require('web.rpc');
const {onWillStart} = owl;
patch(ListController.prototype, 'model_access_rights/static/src/js/list_controller.js.ListController', {
/**
 * This function will used to hide the selected options from the list view
 */
    setup() {
        this._super();
        onWillStart(async () => {
            var self = this
            var result;
            await rpc.query({
                model: 'access.right',
                method: 'hide_buttons',
            }).then(function(data) {
                result = data;
            });
            for (var i = 0; i < result.length; i++) {
                var group = result[i].module + "." + result[i].group_name
                if (self.props.resModel == result[i].model) {
                    if (await self.userService.hasGroup(group)) {
                        if (!this.userService.isAdmin) {
                            if (result[i].is_create_or_update) {
                                self.activeActions.create = false;
                            }
                            if (result[i].is_export) {
                                self.isExportEnable = false
                                self.isExportEnable = false
                            }
                            if (result[i].is_delete) {
                                self.activeActions.delete = false;
                            }
                            if (result[i].is_archive) {
                                self.archiveEnabled = false;
                            } else {
                                self.archiveEnabled = true;
                            }
                        }
                    }
                }
            }
        });
    }
});
