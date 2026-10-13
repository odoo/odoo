import { FileUploadListRenderer } from "../file_upload_list/file_upload_list_renderer";

export class AccountUploadListRenderer extends FileUploadListRenderer {
    // Add warning background color in the ref column if we detect that the record has a duplicated
    getCellClass(column, record) {
        const classNames = super.getCellClass(column, record);
        if (column.name === 'ref' && record.data.duplicated_ref_ids && record.data.duplicated_ref_ids.count !== 0) {
            if (record.data.is_exact_move_duplicate) {
                return `${classNames} table-danger`;
            } else if (record.data.state === 'draft') {
                return `${classNames} table-warning`;
            }
        }
        return classNames;
    }
}
