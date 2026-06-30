import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";

import { EventBus, reactive } from "@odoo/owl";

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

    start(env, { notification: notificationService }) {
        const uploads = reactive({});
        let nextId = 1;
        const bus = new EventBus();

        /**
         * @param {string}                          route
         * @param {FileList|Array<File>}            files
         * @param {Object}                          [params]
         * @param {function(formData): void}        [params.buildFormData]
         * @param {Boolean}                         [params.displayErrorNotification]
         * @returns {reactive}                      upload
         * @returns {XMLHttpRequest}                upload.xhr
         * @returns {FormData}                      upload.data
         * @returns {Number}                        upload.progress
         * @returns {Number}                        upload.loaded
         * @returns {Number}                        upload.total
         * @returns {String}                        upload.title
         * @returns {String||undefined}             upload.type
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
                title: files.length === 1 ? files[0].name : _t("%s Files", files.length),
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
                                content = new DOMParser().parseFromString(content, "text/html");
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
            xhr.addEventListener("error", (ev) => onError(ev.error));
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
