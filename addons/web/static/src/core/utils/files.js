import { humanNumber } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

export const DEFAULT_MAX_FILE_SIZE = 128 * 1024 * 1024;

/**
 * @param {Services["notification"]} notificationService
 * @param {File} file
 * @param {Number} maxUploadSize
 * @returns {boolean}
 */
export function checkFileSize(fileSize, notificationService) {
    const maxUploadSize = session.max_file_upload_size || DEFAULT_MAX_FILE_SIZE;
    if (fileSize > maxUploadSize) {
        notificationService.add(
            _t(
                "The selected file (%(size)sB) is larger than the maximum allowed file size (%(maxSize)sB).",
                { size: humanNumber(fileSize), maxSize: humanNumber(maxUploadSize) }
            ),
            {
                type: "danger",
            }
        );
        return false;
    }
    return true;
}

/**
 * Hook to upload a file to the server.
 * @returns {function}
 */
export function useFileUploader() {
    const http = useService("http");
    const notification = useService("notification");
    /**
     * @param {string} route
     * @param {Object} params
     */
    return async (route, params) => {
        if ((params.ufile && params.ufile.length) || params.file) {
            const fileSize = (params.ufile && params.ufile[0].size) || params.file.size;
            if (!checkFileSize(fileSize, notification)) {
                return null;
            }
        }
        const fileData = await http.post(route, params, "text");
        const parsedFileData = JSON.parse(fileData);
        if (parsedFileData.error) {
            throw new Error(parsedFileData.error);
        }
        return parsedFileData;
    };
}
