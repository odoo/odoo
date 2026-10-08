import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";

/**
 * Helpers of the `<button type="upload" name="method" options="{...}"/>` view
 * button. The options are:
 * - `accept`: accepted types, same syntax as the `accept` attribute of an
 *   `<input type="file">` (".pdf,.xml", "image/*"...). Default: all.
 * - `multiple`: allow to pick several files. Default: true.
 * - `route`: HTTP route receiving the files (`ufile`) instead of calling the
 *   model method `name`.
 * - `dropzone_only`: the button is not shown, the view (or the card) only
 *   gets its dropzone.
 * In a form, `special="upload"` uploads the files without saving the record.
 * The translatable attribute `dropzone-label` is the label of the dropzone
 * shown when files are dragged over the view ("Drop files to upload them to
 * <label>").
 */

/**
 * The uploads of the buttons calling a model method, by id, shown by
 * `UploadProgress` while they run. The uploads to an `options.route` are not
 * in it: the views owning the route show their own progress (product documents).
 */
export const buttonUploads = proxy({});

export function getUploadOptions(clickParams) {
    return evaluateExpr(clickParams.options || "{}");
}

/**
 * Opens the file picker of the browser.
 *
 * @param {{ accept?: string, multiple?: boolean }} [options]
 * @returns {Promise<File[]>} no file if the user cancels
 */
export function pickFiles({ accept, multiple = true } = {}) {
    // an input left by a previous picker that was cancelled
    document.querySelectorAll("input.o_upload_input").forEach((input) => input.remove());
    return new Promise((resolve) => {
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = multiple;
        // visually hidden, but not `hidden` nor transparent: tours and tests act on visible elements
        input.className = "o_upload_input";
        input.style.cssText =
            "position: fixed; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden; clip: rect(0, 0, 0, 0);";
        input.tabIndex = -1;
        if (accept) {
            input.accept = accept;
        }
        // Nothing happens if the user cancels: the input stays, unused, until the next picker
        input.addEventListener("change", () => {
            const files = [...input.files];
            input.remove();
            resolve(files);
        });
        document.body.append(input);
        input.click();
    });
}

/**
 * @param {File[]} files
 * @param {string} [accept] same syntax as the `accept` attribute of an input
 * @returns {{ accepted: File[], rejected: File[] }}
 */
export function filterFiles(files, accept) {
    const patterns = (accept || "")
        .split(",")
        .map((pattern) => pattern.trim().toLowerCase())
        .filter(Boolean);
    if (!patterns.length) {
        return { accepted: files, rejected: [] };
    }
    const isAccepted = ({ name, type }) =>
        patterns.some((pattern) => {
            if (pattern.startsWith(".")) {
                return name.toLowerCase().endsWith(pattern);
            }
            if (pattern.endsWith("/*")) {
                return type.toLowerCase().startsWith(pattern.slice(0, -1));
            }
            return type.toLowerCase() === pattern;
        });
    return {
        accepted: files.filter(isAccepted),
        rejected: files.filter((file) => !isAccepted(file)),
    };
}

/**
 * Sends the files to the server, which calls the method `name` of the button
 * (or the route `options.route`) with them.
 *
 * @param {Object} services services `file_upload` and `notification`
 * @param {Object} params
 * @param {Object} params.clickParams the click params of the button
 * @param {string} params.resModel
 * @param {number[]} [params.resIds]
 * @param {Object} [params.context]
 * @param {File[]} params.files
 * @returns {Promise<Object|false|null>} the action returned by the server (false if
 *      none), null if nothing was uploaded
 */
export async function uploadFiles(
    { file_upload: fileUpload, notification },
    { clickParams, resModel, resIds = [], context = {}, files }
) {
    const options = getUploadOptions(clickParams);
    const { accepted, rejected } = filterFiles(files, options.accept);
    if (rejected.length) {
        notification.add(
            _t(
                "These files have an invalid type and were ignored: %s",
                rejected.map((f) => f.name).join(", ")
            ),
            { type: "warning" }
        );
    }
    if (!accepted.length) {
        return null;
    }
    const upload = await fileUpload.upload(options.route || "/web/dataset/call_upload", accepted, {
        buildFormData(formData) {
            formData.append("model", resModel);
            formData.append("method", clickParams.name || "");
            formData.append("res_ids", JSON.stringify(resIds));
            formData.append("context", JSON.stringify(context));
        },
    });
    if (!options.route) {
        buttonUploads[upload.id] = upload;
    }
    return new Promise((resolve) => {
        const onEnd = ({ detail }) => {
            if (detail.upload.id !== upload.id) {
                return;
            }
            delete buttonUploads[upload.id];
            fileUpload.bus.removeEventListener("FILE_UPLOAD_LOADED", onEnd);
            fileUpload.bus.removeEventListener("FILE_UPLOAD_ERROR", onEnd);
            if (upload.state !== "loaded") {
                return resolve(null);
            }
            const action = upload.response?.result || false;
            if (action.context?.notifications) {
                // messages about the files, e.g. the ones that could not be processed
                for (const [file, message] of Object.entries(action.context.notifications)) {
                    notification.add(message, { title: file, type: "info", sticky: true });
                }
                delete action.context.notifications;
            }
            // the uploaded records are shown, so the help of an empty view is never displayed
            delete action.help;
            resolve(action);
        };
        fileUpload.bus.addEventListener("FILE_UPLOAD_LOADED", onEnd);
        fileUpload.bus.addEventListener("FILE_UPLOAD_ERROR", onEnd);
    });
}
