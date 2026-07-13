/** @odoo-module **/

import { humanNumber } from "@web/core/utils/numbers";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

const DEFAULT_MAX_FILE_SIZE = 128 * 1024 * 1024;

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
                "The selected file (%sB) is over the maximum allowed file size (%sB).",
                humanNumber(fileSize),
                humanNumber(maxUploadSize)
            ),
            {
                type: "danger",
            }
        );
        return false;
    }
    return true;
}

export function resizeBlobImg(blob, params = {}) {
    if (!blob.type || !blob.type.startsWith("image/")) {
        return Promise.reject(new Error(_t("The file is not an image, resizing is not possible")));
    }
    const { width, height, offsetX, offsetY } = {
        width: 256,
        height: 256,
        offsetX: 0.5,
        offsetY: 0.5,
        ...params,
    };
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            if (width < img.width || height < img.height) {
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext("2d");
                ctx.imageSmoothingQuality = "high";
                ctx.mozImageSmoothingEnabled = true;
                ctx.webkitImageSmoothingEnabled = true;
                ctx.msImageSmoothingEnabled = true;
                ctx.imageSmoothingEnabled = true;

                // Keep src image's aspect ratio
                // while drawing in dest image with different ratio
                const srcRatio = img.width / img.height;
                const dWidth = Math.min(Math.floor(height * srcRatio), width);
                const dHeight = Math.min(Math.floor(width / srcRatio), height);

                // Start drawing at some proportion from the edges
                // 0.5 means the image is centered on the image's shortest axis
                const dx = Math.round((width - dWidth) * offsetX);
                const dy = Math.round((height - dHeight) * offsetY);

                ctx.drawImage(img, 0, 0, img.width, img.height, dx, dy, dWidth, dHeight);
                canvas.toBlob(resolve);
            } else {
                resolve(blob);
            }
        };
        img.onerror = () => {
            reject(new Error(_t("The resizing of the image failed")));
        };
        img.src = URL.createObjectURL(blob);
    });
}
