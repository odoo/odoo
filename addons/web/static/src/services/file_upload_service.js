// @ts-check

/** @module @web/services/file_upload_service - XHR-based file upload service with progress tracking and event bus */

import { EventBus, reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
/**
 * Service for uploading files via XHR with progress tracking and error handling.
 * Exposes an EventBus that emits FILE_UPLOAD_ADDED, FILE_UPLOAD_LOADED, and
 * FILE_UPLOAD_ERROR events.
 */
export const fileUploadService = {
    dependencies: ["notification"],
    /**
     * Overridden during tests to return a mocked XHR.
     *
     * @private
     * @returns {XMLHttpRequest}
     */
    createXhr() {
        return new window.XMLHttpRequest();
    },

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ notification: any }} services
     * @returns {{ bus: EventBus, upload: Function, uploads: Record<number, Object> }}
     */
    start(env, { notification: notificationService }) {
        /** @type {Record<number, Object>} */
        const uploads = reactive({});
        let nextId = 1;
        const bus = new EventBus();

        /**
         * @param {string}                          route
         * @param {FileList|Array<File>}            files
         * @param {Object}                          [params]
         * @param {function(FormData): void}        [params.buildFormData]
         * @param {Boolean}                         [params.displayErrorNotification]
         * @returns {Promise<{xhr: XMLHttpRequest, data: FormData, progress: number, loaded: number, total: number, title: string, type: string|undefined, id: number, state: string}>}
         */
        const upload = async (route, files, params = {}) => {
            const xhr = this.createXhr();
            xhr.open("POST", route);
            const formData = new FormData();
            formData.append("csrf_token", odoo.csrf_token);
            for (const file of files) {
                formData.append("ufile", file);
            }
            if (params.buildFormData) {
                params.buildFormData(formData);
            }
            const upload = reactive({
                id: nextId++,
                xhr,
                data: formData,
                progress: 0,
                loaded: 0,
                total: 0,
                state: "pending",
                title:
                    files.length === 1 ? files[0].name : _t("%s Files", files.length),
                type: files.length === 1 ? files[0].type : undefined,
            });
            uploads[upload.id] = upload;
            // Progress listener
            xhr.upload.addEventListener("progress", async (ev) => {
                upload.progress = ev.loaded / ev.total;
                upload.loaded = ev.loaded;
                upload.total = ev.total;
                upload.state = "loading";
            });
            // Load listener
            xhr.addEventListener("load", () => {
                try {
                    handleResponse();
                } catch (e) {
                    onError(e);
                    return;
                }
                delete uploads[upload.id];
                upload.state = "loaded";
                bus.trigger("FILE_UPLOAD_LOADED", { upload });
            });

            /**
             * Parse the XHR response and throw if it indicates an error.
             * Handles JSON-RPC error objects and HTML error pages.
             * @returns {true}
             * @throws {Error} if the response indicates a server error
             */
            function handleResponse() {
                const resp = xhr.responseText ?? xhr.response;
                let error;
                let errorMessage = "";
                if (!(xhr.status >= 200 && xhr.status < 300)) {
                    error = true;
                }
                if (resp) {
                    let content = resp;
                    if (typeof content === "string") {
                        try {
                            content = JSON.parse(content);
                        } catch {
                            try {
                                content = new DOMParser().parseFromString(
                                    content,
                                    "text/html",
                                );
                            } catch {
                                /** pass */
                            }
                        }
                    }
                    // Not sure what to do if the content is neither JSON nor HTML
                    // Let's the call be successful then....
                    if (error && content instanceof Document) {
                        errorMessage = content.body.textContent;
                    } else if (content instanceof Object) {
                        if (content.error) {
                            // https://www.jsonrpc.org/specification#error_object
                            error = true;
                            if (content.error.data) {
                                // JsonRPCDispatcher.handle_error and http.serialize_exception
                                errorMessage = `${content.error.data.name}: ${content.error.data.message}`;
                            } else {
                                errorMessage = content.error.message || errorMessage;
                            }
                        }
                    }
                }
                if (error) {
                    throw new Error(errorMessage);
                }
                return true;
            }

            /**
             * Handle upload failure: remove from tracker, show notification,
             * and emit FILE_UPLOAD_ERROR event.
             * @param {Error} [error]
             */
            function onError(error) {
                const defaultErrorMessage = _t("An error occured while uploading.");
                delete uploads[upload.id];
                upload.state = "error";
                const displayError = params.displayErrorNotification ?? true;
                // Disable this option if you need more explicit error handling.
                if (displayError) {
                    notificationService.add(error?.message || defaultErrorMessage, {
                        type: "danger",
                        sticky: true,
                    });
                }
                bus.trigger("FILE_UPLOAD_ERROR", { upload });
            }
            // Error listener
            xhr.addEventListener("error", (ev) =>
                onError(/** @type {any} */ (ev).error),
            );
            // Abort listener, considered as error
            xhr.addEventListener("abort", async () => {
                delete uploads[upload.id];
                upload.state = "abort";
                bus.trigger("FILE_UPLOAD_ERROR", { upload });
            });
            xhr.send(formData);
            bus.trigger("FILE_UPLOAD_ADDED", { upload });
            return upload;
        };

        return { bus, upload, uploads };
    },
};

registry.category("services").add("file_upload", fileUploadService);
