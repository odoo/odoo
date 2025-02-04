import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";

import { EventBus, reactive } from "@odoo/owl";
import { UploadProgressService } from "./upload_progress_service";
import { fileProgressManager, fileProgressBar } from "./upload_utils";

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
        let fileId = 0;
        const uploads = reactive({});
        let nextId = 1;
        const bus = new EventBus();
        registry.category("main_components").add("UploadProgressService", {
            Component: UploadProgressService,
        });

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
            if (fileProgressManager.isCancelAllUpload()) {
                return;
            }
            fileProgressBar.uploadInProgress = true;
            const startTime = Date.now();
            const sortedFiles = Array.from(files);
            // Check if there are multiple files for remove/hide the cancel button
            fileProgressBar.multipleFiles = sortedFiles.length > 1;
            fileId = fileProgressManager.prepareFile(sortedFiles, notificationService, fileId);
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
            const filesToUpload = sortedFiles.length > 0 ? sortedFiles : [];
            // Progress listener
            xhr.upload.addEventListener("progress", async (ev) => {
                const remainingTime = fileProgressManager.calculateTime(startTime, ev);
                fileProgressManager.uploadInProgress(filesToUpload, remainingTime, ev);
                upload.progress = ev.loaded / ev.total;
                upload.loaded = ev.loaded;
                upload.total = ev.total;
                upload.state = "loading";
            });
            // Load listener
            xhr.addEventListener("load", () => {
                delete uploads[upload.id];
                upload.state = "loaded";
                fileProgressManager.fileUploadLoaded(filesToUpload);
                fileProgressBar.uploadInProgress = false;
                bus.trigger("FILE_UPLOAD_LOADED", { upload });
                // Clear files when the upload completes
                fileProgressManager.clearUploadedFiles();
            });
            // Error listener
            xhr.addEventListener("error", async () => {
                delete uploads[upload.id];
                upload.state = "error";
                fileProgressManager.fileInError(filesToUpload);
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
            fileProgressBar.xhr = xhr;
            return upload;
        };

        return { bus, upload, uploads, fileProgressBar };
    },
};

registry.category("services").add("file_upload", fileUploadService);
