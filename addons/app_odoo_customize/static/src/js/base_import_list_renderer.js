/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ImportModuleListRenderer } from "@base_import_module/base_import_list_renderer";

patch(ImportModuleListRenderer.prototype, {
    async onCellClicked(record, column, ev) {
        if (record._values.module_type && record._values.module_type === 'odooapp.cn') {
            const re_action = {
                name: "more_info",
                res_model: "ir.module.module",
                res_id: record.resId,
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                context: {
                    'module_name': record._values.name,
                    'module_type': record._values.module_type,
                }
            }
            this.env.services.action.doAction(re_action);
        }
        else{
            super.onCellClicked(record, column, ev);
        }
    }
})
