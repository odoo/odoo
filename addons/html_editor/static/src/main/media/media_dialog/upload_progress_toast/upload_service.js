import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { UploadProgressToast } from "./upload_progress_toast";
import { fileProgressManager } from "@web/core/file_upload/upload_utils";
import { _t } from "@web/core/l10n/translation";
import { checkFileSize } from "@web/core/utils/files";
import { humanNumber } from "@web/core/utils/numbers";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { sprintf } from "@web/core/utils/strings";
import { reactive } from "@odoo/owl";

export const AUTOCLOSE_DELAY = 3000;
export const AUTOCLOSE_DELAY_LONG = 8000;

export const uploadService = {
    dependencies: ["notification"],
    start(env, { notification }) {
        let fileId = 0;
        const progressToast = reactive({
            files: {},
            isVisible: false,
            close: (value) => {
                progressToast.isVisible = value;
            },
        });

        registry.category("main_components").add("UploadProgressToast", {
            Component: UploadProgressToast,
        });

        const addFile = (file) => {
            progressToast.files[file.id] = file;
            progressToast.isVisible = true;
            return progressToast.files[file.id];
        };

        const deleteFile = (fileId) => {
            delete progressToast.files[fileId];
            if (!Object.keys(progressToast.files).length) {
                progressToast.isVisible = false;
            }
        };
        return {
            get progressToast() {
                return progressToast;
            },
            get fileId() {
                return fileId;
            },
            addFile,
            deleteFile,
            incrementId() {
                fileId++;
            },
            uploadUrl: async (url, { resModel, resId }, onUploaded) => {
                const attachment = await rpc("/html_editor/attachment/add_url", {
                    url,
                    res_model: resModel,
                    res_id: resId,
                });
                await onUploaded(attachment);
            },
            /**
             * This takes an array of files (from an input HTMLElement), and
             * uploads them while managing the UploadProgressToast.
             *
             * @param {Array<File>} files
             * @param {Object} options
             * @param {Function} onUploaded
             */
            uploadFiles: async (files, { resModel, resId, isImage }, onUploaded) => {
                progressToast.uploadInProgress = true;
                const startTime = Date.now();
                // Upload the smallest file first to block the user the least possible.
                const sortedFiles = Array.from(files).sort((a, b) => a.size - b.size);
                for (const file of sortedFiles) {
                    let fileSize = file.size;
                    if (!checkFileSize(fileSize, notification)) {
                        return null;
                    }
                    if (!fileSize) {
                        fileSize = "";
                    } else {
                        fileSize = humanNumber(fileSize) + "B";
                    }

                    const id = ++fileId;
                    file.progressToastId = id;
                    // This reactive object, built based on the files array,
                    // is given as a prop to the UploadProgressToast.
                    addFile({
                        id,
                        name: file.name,
                        size: fileSize,
                    });
                }

                // Upload one file at a time: no need to parallel as upload is
                // limited by bandwidth.
                for (const sortedFile of sortedFiles) {
                    const file = progressToast.files[sortedFile.progressToastId];
                    let dataURL;
                    try {
                        dataURL = await getDataURLFromFile(sortedFile);
                    } catch {
                        deleteFile(file.id);
                        env.services.notification.add(
                            sprintf(_t('Could not load the file "%s".'), sortedFile.name),
                            { type: "danger" }
                        );
                        continue;
                    }
                    try {
                        const xhr = new XMLHttpRequest();
                        progressToast.xhr = xhr;
                        xhr.upload.addEventListener("progress", (ev) => {
                            const rpcComplete = (ev.loaded / ev.total) * 100;
                            const remainingTime = fileProgressManager.calculateTime(startTime, ev);
                            Object.values(progressToast.files).forEach((file) => {
                                const fileDetails = progressToast.files[file.id];
                                fileProgressManager.remainingTime(fileDetails, remainingTime);
                            });
                            file.progress = rpcComplete;
                        });
                        xhr.upload.addEventListener("load", function () {
                            // Don't show yet success as backend code only starts now
                            file.progress = 100;
                        });
                        const attachment = await rpc(
                            "/html_editor/attachment/add_data",
                            {
                                name: file.name,
                                data: dataURL.split(",")[1],
                                res_id: resId,
                                res_model: resModel,
                                is_image: !!isImage,
                                width: 0,
                                quality: 0,
                            },
                            { xhr }
                        );
                        if (attachment.error) {
                            file.hasError = true;
                            file.errorMessage = attachment.error;
                        } else {
                            if (attachment.mimetype === "image/webp") {
                                // Generate alternate format for reports.
                                const image = document.createElement("img");
                                image.src = `data:image/webp;base64,${dataURL.split(",")[1]}`;
                                await new Promise((resolve) =>
                                    image.addEventListener("load", resolve)
                                );
                                const canvas = document.createElement("canvas");
                                canvas.width = image.width;
                                canvas.height = image.height;
                                const ctx = canvas.getContext("2d");
                                ctx.fillStyle = "rgb(255, 255, 255)";
                                ctx.fillRect(0, 0, canvas.width, canvas.height);
                                ctx.drawImage(image, 0, 0);
                                const altDataURL = canvas.toDataURL("image/jpeg", 0.75);
                                await rpc(
                                    "/html_editor/attachment/add_data",
                                    {
                                        name: file.name.replace(/\.webp$/, ".jpg"),
                                        data: altDataURL.split(",")[1],
                                        res_id: attachment.id,
                                        res_model: "ir.attachment",
                                        is_image: true,
                                        width: 0,
                                        quality: 0,
                                    },
                                    { xhr }
                                );
                            }
                            file.uploaded = true;
                            await onUploaded(attachment);
                        }
                        // If there's an error, display the error message for longer
                        const message_autoclose_delay = file.hasError
                            ? AUTOCLOSE_DELAY_LONG
                            : AUTOCLOSE_DELAY;
                        setTimeout(() => deleteFile(file.id), message_autoclose_delay);
                    } catch (error) {
                        file.hasError = true;
                        setTimeout(() => deleteFile(file.id), AUTOCLOSE_DELAY_LONG);
                        throw error;
                    }
                }
            },
        };
    },
};

registry.category("services").add("upload", uploadService);
