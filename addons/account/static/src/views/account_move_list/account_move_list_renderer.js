import { BillGuide } from "@account/components/bill_guide/bill_guide";
import { FileUploadListRenderer } from "../file_upload_list/file_upload_list_renderer";

export class AccountMoveListRenderer extends FileUploadListRenderer {
    static template = "account.AccountMoveListRenderer";
    static components = {
        ...FileUploadListRenderer.components,
        BillGuide,
    };

    // Add warning background color in the ref column if we detect that the move has a duplicated
    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (column.name === 'ref' && record.data.duplicated_ref_ids && record.data.duplicated_ref_ids.count !== 0) {
            return `${classNames} table-warning`;
        }
        return classNames;
    }
}
