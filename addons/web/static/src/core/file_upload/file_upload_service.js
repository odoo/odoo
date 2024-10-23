import { _t } from "@web/core/l10n/translation";
import { registry } from "../registry";

import { EventBus, reactive } from "@odoo/owl";
import { checkFileSize } from "@web/core/utils/files";
import { humanNumber } from "@web/core/utils/numbers";
import { UploadProgressManager } from "./upload_progress_service";

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
        const fileProgressBar = reactive({
            files: {},
            uploadInProgress: false,
            isVisible: false,
            xhr: 0,
            multipleFiles: false,
            cancelAllUpload: false,
            totalFilesCount: 0,
        });
        let nextId = 1;
        const bus = new EventBus();
        registry.category("main_components").add("UploadProgressManager", {
            Component: UploadProgressManager,
        });

        const addFile = (file) => {
            if (file.name && !fileProgressBar.files[file.id]) {
                fileProgressBar.files[file.id] = file;
                fileProgressBar.isVisible = true;
            }
        };

        const clearFiles = () => {
            for (const [fileId, file] of Object.entries(fileProgressBar.files)) {
                if (file.uploaded) {
                    setTimeout(() => {
                        delete fileProgressBar.files[fileId];
                        if (Object.keys(fileProgressBar.files).length === 0) {
                            fileProgressBar.isVisible = false;
                            fileProgressBar.totalFilesCount = 0;
                        }
                    }, 5000);
                }
            }
        };
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
            if (fileProgressBar.cancelAllUpload) {
                delete fileProgressBar.files[fileId];
                fileProgressBar.isVisible = false;
                fileProgressBar.cancelAllUpload = false;
                fileProgressBar.totalFilesCount = 0;
                return;
            }
            fileProgressBar.uploadInProgress = true;
            const startTime = Date.now();
            const sortedFiles = Array.from(files);
            // Check if there are multiple files for remove/hide the cancel button
            fileProgressBar.multipleFiles = sortedFiles.length > 1;
            for (const file of sortedFiles) {
                let fileSize = file.size;
                if (!checkFileSize(fileSize, notificationService)) {
                    return null;
                }
                fileSize = fileSize ? humanNumber(fileSize) + "B" : "";
                const id = ++fileId;
                file.progressToastId = id;
                // Create a wrapped file object with metadata (copy of original file)
                const fileDetails = {
                    id,
                    name: file.name,
                    size: fileSize,
                };
                // Add the file to the progress bar only if it's valid
                addFile(fileDetails);
            }
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
                const elapsedTime = (Date.now() - startTime) / 1000;
                const totalUploadTime = (elapsedTime / ev.loaded) * ev.total;
                const remainingTime = Math.max(totalUploadTime - elapsedTime, 0);
                if (filesToUpload) {
                    Object.values(filesToUpload).forEach((file) => {
                        if (file.progressToastId) {
                            const fileDetails = fileProgressBar.files[file.progressToastId];
                            if (fileDetails) {
                                fileDetails.progress = (ev.loaded / ev.total) * 100;
                                fileDetails.remainingTime = `${Math.floor(
                                    remainingTime / 60
                                )}m:${Math.round(remainingTime % 60)}s`;
                                fileDetails.cancel_upload = false;
                            }
                        }
                    });
                }
                upload.progress = ev.loaded / ev.total;
                upload.loaded = ev.loaded;
                upload.total = ev.total;
                upload.state = "loading";
            });
            // Load listener
            xhr.addEventListener("load", () => {
                delete uploads[upload.id];
                upload.state = "loaded";
                if (filesToUpload) {
                    Object.values(filesToUpload).forEach((file) => {
                        if (file.progressToastId) {
                            const fileDetails = fileProgressBar.files[file.progressToastId];
                            if (fileDetails) {
                                fileDetails.progress = 100;
                                fileDetails.uploaded = true;
                            }
                            if (fileDetails.uploaded) {
                                fileProgressBar.totalFilesCount += 1;
                            }
                        }
                    });
                }
                fileProgressBar.uploadInProgress = false;
                bus.trigger("FILE_UPLOAD_LOADED", { upload });
                // Clear files when the upload completes
                clearFiles();
            });
            // Error listener
            xhr.addEventListener("error", async () => {
                delete uploads[upload.id];
                upload.state = "error";
                if (filesToUpload) {
                    Object.values(filesToUpload).forEach((file) => {
                        if (file.progressToastId) {
                            const fileDetails = fileProgressBar.files[file.progressToastId];
                            if (fileDetails) {
                                fileDetails.hasError = true;
                            }
                        }
                    });
                }
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
