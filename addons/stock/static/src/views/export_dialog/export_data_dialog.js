import {ExportDataDialog} from "@web/views/view_dialogs/export_data_dialog";
import {patch} from "@web/core/utils/patch";

patch(ExportDataDialog.prototype, {
    setDefaultExportList() {
        if (this.props.root.resModel !== "stock.quant") {
            super.setDefaultExportList();
            return;
        }
        const templateName = "Template for Inventory Adjustments";
        const defaultTemplates = this.templates.filter((template) => template.display_name === templateName);
        if (defaultTemplates.length >= 1) {
            this.state.templateId = defaultTemplates[0].id
        }
        super.setDefaultExportList()
    }
});