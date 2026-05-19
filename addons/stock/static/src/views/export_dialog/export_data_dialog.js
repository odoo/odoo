import {ExportDataDialog} from "@web/views/view_dialogs/export_data_dialog";
import {patch} from "@web/core/utils/patch";

patch(ExportDataDialog.prototype, {
    setDefaultExportList() {
        if (this.props.root.resModel !== "stock.quant") {
            super.setDefaultExportList();
            return;
        }
        const templateId = this.props.context?.stock_export_template_id;
        if (templateId && this.templates.some((template) => template.id === templateId)) {
            this.state.templateId = templateId;
        }
        super.setDefaultExportList();
    }
});
