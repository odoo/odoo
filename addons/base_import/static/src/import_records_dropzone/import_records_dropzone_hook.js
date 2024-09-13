import { _t } from "@web/core/l10n/translation";
import { ImportRecordsDropzone } from "./import_records_dropzone";
import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { useService } from "@web/core/utils/hooks";

/**
 * @param {Object} targetRef
 * @param {string} resModel
 * @param {function} onDropFile
 */
export function useImportRecordsDropzone (targetRef, resModel, onDropFile) {
    const notification = useService("notification");
    useCustomDropzone(targetRef, ImportRecordsDropzone, {
        resModel,
        /** @param {Event} event */
        onDrop: async event => {
            const { files } = event.dataTransfer;
            if (files.length === 0) {
                notification.add(_t("Please upload an Excel (.xls or .xlsx) or .csv file to import."), {
                    type: "danger",
                });
            } else if (files.length > 1) {
                notification.add(_t("Please upload a single file."), {
                    type: "danger",
                });
            } else {
                const file = files[0];
                const isValidFile = file.name.endsWith(".csv")
                                 || file.name.endsWith(".xls")
                                 || file.name.endsWith(".xlsx");
                if (!isValidFile) {
                    notification.add(_t("Please upload an Excel (.xls or .xlsx) or .csv file to import."), {
                        type: "danger",
                    });
                } else {
                    onDropFile(file);
                }
            }
        }
    });
}
