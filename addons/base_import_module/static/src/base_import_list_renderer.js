import { ListRenderer } from "@web/views/list/list_renderer";

export class ImportModuleListRenderer extends ListRenderer {

    get hasSelectors() {
        return super.hasSelectors && this.props.list.records.every(record => !record._values.from_appstore);
    }

    async onCellClicked(record, column, ev) {
        if (record._values.from_appstore) {
            const re_action = {
                name: "more_info",
                res_model: "ir.module.module",
                res_id: -1,
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                context: {
                    'module_name': record._values.name,
                    'module_type': 'industries',
                }
            }
            this.env.services.action.doAction(re_action);
        }
        else{
            super.onCellClicked(record, column, ev);
        }
    }
}
