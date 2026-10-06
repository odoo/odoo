import { trackedUpload } from "@web/core/file_upload/tracked_upload";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { checkFileSize } from "@web/core/utils/files";

/**
 * Helpers of the `<button type="upload" name="method" options="{...}"/>` view
 * button. The options are:
 * - `accept`: accepted types, same syntax as the `accept` attribute of an
 *   `<input type="file">` (".pdf,.xml", "image/*"...). Default: all.
 * - `multiple`: allow to pick several files. Default: true.
 * - `max_size`: the maximum size of a file, in bytes. Default: the upload
 *   limit of the server. The larger files are left out with a warning.
 * - `dropzone_only`: the button is not shown, the view (or the card) only
 *   gets its dropzone.
 * - `model`: the model whose method `name` is called (on no record), instead
 *   of the model of the view. The button `context` passes what it needs, and a
 *   form is not saved first.
 */

export function getUploadOptions({ options }) {
    return typeof options === "object" ? options : evaluateExpr(options || "{}");
}

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
        input.addEventListener("change", () => {
            const files = [...input.files];
            input.remove();
            resolve(files);
        });
        document.body.append(input);
        input.click();
    });
}

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
 * @returns {Promise<Object|false|null>} the action returned by the server, false
 *      if none, null if nothing was uploaded
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
    const sendable = accepted.filter((file) =>
        checkFileSize(file.size, notification, options.max_size || undefined)
    );
    if (!sendable.length) {
        return null;
    }
    const upload = await trackedUpload(fileUpload, "/web/dataset/call_upload", sendable, {
        buildFormData(formData) {
            formData.append("model", resModel);
            formData.append("method", clickParams.name || "");
            formData.append("res_ids", JSON.stringify(resIds));
            formData.append("context", JSON.stringify(context));
        },
    });
    if (upload.state !== "loaded") {
        return null;
    }
    const action = upload.response?.result || false;
    if (action.context?.notifications) {
        for (const [file, message] of Object.entries(action.context.notifications)) {
            notification.add(message, { title: file, type: "info", sticky: true });
        }
        delete action.context.notifications;
    }
    // the uploaded records are shown, so the help of an empty view is never displayed
    delete action.help;
    return action;
}
