/** @odoo-module */
/**
 * This file will used to hide the selected options from the list view
 */
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { patch} from "@web/core/utils/patch";
var rpc = require('web.rpc');
const {onWillStart} = owl;
patch(KanbanController.prototype, 'model_access_rights/static/src/js/list_controller.js.KanbanController', {
/**
 * This function will used to hide the selected options from the Kanban view
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
                    if (await self.model.user.hasGroup(group)) {
                        if (!self.model.user.isAdmin) {
                            if (result[i].is_create_or_update) {
                                self.props.archInfo.activeActions.create=false
                                self.props.archInfo.activeActions.edit=false
                            }
                            if (result[i].is_delete) {
                            self.props.archInfo.activeActions.delete=false
                            }
                        }
                    }
                }
            }
        });
    }
});
