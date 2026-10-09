import { humanNumber } from "@web/core/utils/numbers";
import { trackedUpload } from "@web/core/file_upload/tracked_upload";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

export const DEFAULT_MAX_FILE_SIZE = 128 * 1024 * 1024;

/**
 * @param {Number} fileSize
 * @param {Services["notification"]} notificationService
 * @param {Number} [maxUploadSize] default: the upload limit of the server
 * @returns {boolean}
 */
export function checkFileSize(
    fileSize,
    notificationService,
    maxUploadSize = session.max_file_upload_size || DEFAULT_MAX_FILE_SIZE
) {
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
    const fileUpload = useService("file_upload");
    const notification = useService("notification");
    /**
     * @param {string} route
     * @param {Object} params `ufile` (the files) and the other fields of the request
     */
    return async (route, params) => {
        const { ufile = [], ...fields } = params;
        delete fields.csrf_token; // added by the service
        if (ufile.some((file) => !checkFileSize(file.size, notification))) {
            return null;
        }
        const upload = await trackedUpload(fileUpload, route, ufile, {
            buildFormData(formData) {
                for (const [name, value] of Object.entries(fields)) {
                    if (value !== undefined) {
                        formData.append(name, value);
                    }
                }
            },
            displayErrorNotification: false,
        });
        if (upload.state === "abort") {
            return null;
        }
        if (upload.state !== "loaded") {
            const error = upload.response?.error;
            throw new Error(error?.message || error || _t("An error occurred while uploading."));
        }
        return upload.response;
    };
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
