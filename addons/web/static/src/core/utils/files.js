/** @odoo-module **/

import { humanNumber } from "@web/core/utils/numbers";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "./strings";

const DEFAULT_MAX_FILE_SIZE = 128 * 1024 * 1024;

/**
 * @param {number} fileSize
 * @param {Services["notification"]} [notificationService]
 * @returns {boolean}
 */
export function checkFileSize(fileSize, notificationService) {
    const maxUploadSize = session.max_file_upload_size || DEFAULT_MAX_FILE_SIZE;
    if (fileSize > maxUploadSize) {
        if (notificationService) {
            notificationService.add(
                sprintf(
                    _t("The selected file (%sB) is over the maximum allowed file size (%sB)."),
                    humanNumber(fileSize),
                    humanNumber(maxUploadSize)
                ),
                {
                    type: "danger",
                }
            );
        }
        return false;
    }
    return true;
}
