import { proxy } from "@odoo/owl";

/**
 * The uploads shown by `UploadProgress` until they end.
 */
export const trackedUploads = proxy({});

/**
 * Uploads the files with the `file_upload` service, showing their progress.
 *
 * @returns {Promise<Object>} the upload, once loaded, failed or cancelled (see its `state`)
 */
export async function trackedUpload(fileUpload, route, files, params) {
    const upload = await fileUpload.upload(route, files, params);
    trackedUploads[upload.id] = upload;
    return new Promise((resolve) => {
        const onEnd = ({ detail }) => {
            if (detail.upload.id !== upload.id) {
                return;
            }
            delete trackedUploads[upload.id];
            fileUpload.bus.removeEventListener("FILE_UPLOAD_LOADED", onEnd);
            fileUpload.bus.removeEventListener("FILE_UPLOAD_ERROR", onEnd);
            resolve(upload);
        };
        fileUpload.bus.addEventListener("FILE_UPLOAD_LOADED", onEnd);
        fileUpload.bus.addEventListener("FILE_UPLOAD_ERROR", onEnd);
    });
}
