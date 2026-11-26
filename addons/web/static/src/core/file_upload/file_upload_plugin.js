import { Plugin, signal, usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { makeErrorFromResponse } from "@web/core/network/rpc";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { evaluateExpr } from "@web/core/py_js/py";
import { services } from "@web/core/services";
import { DEFAULT_MAX_FILE_SIZE } from "@web/core/utils/files";
import { humanNumber } from "@web/core/utils/numbers";
import { session } from "@web/session";

/**
 * The file uploads of the web client, with `usePlugin(FileUploadPlugin)`:
 * - `sendFiles(route, params, options)`: posts files to a route, showing the
 *   progress card, e.g. `FileInput`, `<button type="upload"/>`.
 * - `pickFiles(options)`: opens the file picker of the browser.
 *
 * The upload options (`options` of `<button type="upload"/>`, as an object or a
 * Python expression) are:
 * - `accept`: accepted types, same syntax as the `accept` attribute of an
 *   `<input type="file">` (".pdf,.xml", "image/*"...). Default: all.
 * - `multiple`: allow to pick several files. Default: true.
 * - `max_size`: the upload limit, in bytes. Default: the one of the server.
 * They only help the user: the server validates the files itself.
 * `sendFiles` also takes a `signal` (`AbortSignal`) cancelling the upload.
 */
export class FileUploadPlugin extends Plugin {
    #notification = usePlugin(NotificationPlugin);
    #nextId = 1;
    /**
     * The uploads shown by `UploadProgress`: the running ones, and the ones
     * just done. The plugin being global, they survive the navigation.
     */
    uploads = signal.Array([]);

    /**
     * Posts the files (`ufile`) and the other fields of `params` to the route,
     * showing the progress card, and waits for the end. The files of a type
     * not in `accept` or larger than `max_size` are left out with a warning,
     * and nothing is sent if the others together are larger than `max_size`.
     * E.g.:
     * `await sendFiles("/web/binary/upload_attachment", { ufile: files, model, id })`
     *
     * @param {string} route
     * @param {Object} params
     * @param {Object|string} [options] `accept`, `max_size` and `signal` (see above)
     * @returns {Promise<Object|null>} the JSON response, null if nothing was
     *      sent (all files left out, too large) or the upload was cancelled
     * @throws {Error} the error of the server: an RPC error if it answered one
     */
    async sendFiles(route, params, options) {
        const { ufile = [], ...fields } = params;
        const { accept, max_size, signal: abortSignal } = this.#getOptions(options);
        const maxSize = max_size || session.max_file_upload_size || DEFAULT_MAX_FILE_SIZE;
        const files = this.#filterFiles(ufile, accept, maxSize);
        if (ufile.length && !files.length) {
            return null;
        }
        const size = files.reduce((total, file) => total + file.size, 0);
        if (size > maxSize) {
            this.#notification.add(
                _t(
                    "The selected files (%(size)sB) are larger than the maximum upload size (%(maxSize)sB).",
                    { size: humanNumber(size), maxSize: humanNumber(maxSize) }
                ),
                { type: "danger" }
            );
            return null;
        }
        const upload = await this.#send(route, files, fields, abortSignal);
        if (upload.state === "abort") {
            return null;
        }
        const error = upload.response?.error;
        if (error) {
            throw typeof error === "string" ? new Error(error) : makeErrorFromResponse(error);
        }
        if (upload.state !== "loaded") {
            throw new Error(upload.error || _t("An error occurred while uploading."));
        }
        return upload.response;
    }

    /**
     * Opens the file picker of the browser. The browser opens it only during a
     * user gesture: call it in the click handler, before any other `await`.
     *
     * @param {Object|string} [options] `accept` and `multiple` (see above)
     * @returns {Promise<File[]>} the picked files, none if cancelled
     */
    pickFiles(options) {
        const { accept, multiple = true } = this.#getOptions(options);
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
            const done = () => {
                const files = [...input.files];
                input.remove();
                resolve(files);
            };
            input.addEventListener("change", done);
            input.addEventListener("cancel", done);
            document.body.append(input);
            input.click();
        });
    }

    #getOptions(options) {
        return typeof options === "string" ? evaluateExpr(options) : options || {};
    }

    /**
     * @returns {File[]} the files of an accepted type and not larger than
     *      `maxSize`, the others being notified
     */
    #filterFiles(files, accept, maxSize) {
        const patterns = (accept || "")
            .split(",")
            .map((pattern) => pattern.trim().toLowerCase())
            .filter(Boolean);
        const isAccepted = ({ name, type }) =>
            !patterns.length ||
            patterns.some((pattern) => {
                if (pattern.startsWith(".")) {
                    return name.toLowerCase().endsWith(pattern);
                }
                if (pattern.endsWith("/*")) {
                    return type.toLowerCase().startsWith(pattern.slice(0, -1));
                }
                return type.toLowerCase() === pattern;
            });
        const rejected = files.filter((file) => !isAccepted(file));
        if (rejected.length) {
            this.#notification.add(
                _t(
                    "These files have an invalid type and were ignored: %s",
                    rejected.map((f) => f.name).join(", ")
                ),
                { type: "warning" }
            );
        }
        const tooLarge = files.filter((file) => isAccepted(file) && file.size > maxSize);
        if (tooLarge.length) {
            this.#notification.add(
                _t(
                    "These files are larger than the maximum upload size (%(maxSize)sB) and were ignored: %(files)s",
                    { maxSize: humanNumber(maxSize), files: tooLarge.map((f) => f.name).join(", ") }
                ),
                { type: "warning" }
            );
        }
        return files.filter((file) => isAccepted(file) && file.size <= maxSize);
    }

    /**
     * Sends the request, shown in the progress card until it ends.
     *
     * @returns {Promise<Object>} once ended: `state` is "loaded", "error" or
     *      "abort" (cancelled in the card or by the signal), `response` the
     *      parsed JSON response and `error` the text of a server error page
     */
    #send(route, files, fields, abortSignal) {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", route);
        const formData = new FormData();
        formData.append("csrf_token", odoo.csrf_token);
        for (const file of files) {
            formData.append("ufile", file);
        }
        for (const [name, value] of Object.entries(fields)) {
            if (value !== undefined) {
                formData.append(name, value);
            }
        }
        const upload = {
            id: this.#nextId++,
            title: files.length === 1 ? files[0].name : _t("%s Files", files.length),
            progress: signal(0),
            done: signal(false),
            abort: () => xhr.abort(),
        };
        this.uploads().push(upload);
        const remove = () => {
            const uploads = this.uploads();
            uploads.splice(uploads.indexOf(upload), 1);
        };
        const { promise, resolve } = Promise.withResolvers();
        const end = (result) => {
            if (result.state === "loaded") {
                upload.progress.set(1);
                upload.done.set(true);
                setTimeout(remove, 3000);
            } else {
                remove();
            }
            resolve(result);
        };
        xhr.upload.addEventListener("progress", (ev) => {
            upload.progress.set(ev.loaded / ev.total);
        });
        xhr.addEventListener("load", () => {
            const text = xhr.responseText ?? xhr.response;
            let response, error;
            try {
                response = typeof text === "string" ? JSON.parse(text) : text;
            } catch {
                // a page of the server: an error (413...), or the login page of an expired session
                if (xhr.status >= 400) {
                    error = new DOMParser()
                        .parseFromString(text, "text/html")
                        .body.textContent.trim();
                }
            }
            const ok = xhr.status >= 200 && xhr.status < 300 && response;
            end({ state: ok ? "loaded" : "error", response, error });
        });
        xhr.addEventListener("error", () => end({ state: "error" }));
        xhr.addEventListener("abort", () => end({ state: "abort" }));
        abortSignal?.addEventListener("abort", () => xhr.abort());
        xhr.send(formData);
        return promise;
    }
}

services.add(FileUploadPlugin);
