/** @odoo-module */
import { ListRenderer } from "@web/views/list/list_renderer";

export class ImportModuleListRenderer extends ListRenderer {

    get hasSelectors() {
        return super.hasSelectors && this.props.list.records.every(record => record._values.module_type != 'industries');
    }

    async onCellClicked(record, column, ev) {
        if (record._values.module_type && record._values.module_type !== 'official') {
            const re_action = {
                name: "more_info",
                res_model: "ir.module.module",
                res_id: -1,
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
}
