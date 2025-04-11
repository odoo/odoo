import { useService } from "@web/core/utils/hooks";
import { ProductMatrixDialog } from "./product_matrix_dialog";

export function useMatrixConfigurator() {
    const dialog = useService("dialog");

    const openDialog = (rootRecord, jsonInfo, productTemplateId, editedCellAttributes) => {
        const infos = JSON.parse(jsonInfo);
        dialog.add(ProductMatrixDialog, {
            header: infos.header,
            rows: infos.matrix,
            editedCellAttributes: editedCellAttributes.toString(),
            product_template_id: productTemplateId,
            record: rootRecord,
        });
    };

    const open = async (record, edit) => {
        const rootRecord = record.model.root;

        // fetch matrix information from server;
        await rootRecord.update({
            grid_product_tmpl_id: record.data.product_template_id,
        });

        const updatedLineAttributes = [];
        if (edit) {
            // provide attributes of edited line to automatically focus on matching cell in the matrix
            for (const ptnvav of record.data.product_no_variant_attribute_value_ids.records) {
                updatedLineAttributes.push(ptnvav.resId);
            }
            for (const ptav of record.data.product_template_attribute_value_ids.records) {
                updatedLineAttributes.push(ptav.resId);
            }
            updatedLineAttributes.sort((a, b) => a - b);
        }

        openDialog(
            rootRecord,
            rootRecord.data.grid,
            record.data.product_template_id.id,
            updatedLineAttributes
        );

        if (!edit) {
            // remove new line used to open the matrix
            rootRecord.data.order_line.delete(record);
        }
    };

    return { open };
}
