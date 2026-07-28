/** @odoo-module **/

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

    start(env, { notificationService }) {
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
                delete uploads[upload.id];
                upload.state = "loaded";
                bus.trigger("FILE_UPLOAD_LOADED", { upload });
            });
            // Error listener
            xhr.addEventListener("error", async () => {
                delete uploads[upload.id];
                upload.state = "error";
                // Disable this option if you need more explicit error handling.
                if (
                    params.displayErrorNotification !== undefined &&
                    params.displayErrorNotification
                ) {
                    notificationService.add(_t("An error occured while uploading."), {
                        title: _t("Error"),
                        sticky: true,
                    });
                }
                bus.trigger("FILE_UPLOAD_ERROR", { upload });
            });
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
