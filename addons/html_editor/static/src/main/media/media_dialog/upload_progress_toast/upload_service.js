import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { UploadProgressToast } from "./upload_progress_toast";
import { _t } from "@web/core/l10n/translation";
import { checkFileSize } from "@web/core/utils/files";
import { humanNumber } from "@web/core/utils/numbers";
import { getDataURLFromFile } from "@web/core/utils/urls";
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
        });

        registry.category("main_components").add("UploadProgressToast", {
            Component: UploadProgressToast,
            props: {
                close: () => (progressToast.isVisible = false),
            },
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

        const convertWebpToJpeg = async (dataURL, name, attachmentId) => {
            const image = document.createElement("img");
            image.src = `data:image/webp;base64,${dataURL.split(",")[1]}`;
            await new Promise((res, rej) => {
                image.onload = res;
                image.onerror = rej;
            });

            const canvas = document.createElement("canvas");
            canvas.width = image.width;
            canvas.height = image.height;

            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "white";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(image, 0, 0);

            const altDataURL = canvas.toDataURL("image/jpeg", 0.75);

            await rpc("/web_editor/attachment/add_data", {
                name: name.replace(/\.webp$/, ".jpg"),
                data: altDataURL.split(",")[1],
                res_id: attachmentId,
                res_model: "ir.attachment",
                is_image: true,
                width: 0,
                quality: 0,
            });
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
             * @param {Function} setAbortCallback // Optional - To abort uploads
             */
            uploadFiles: async (
                files,
                { resModel, resId, isImage },
                onUploaded,
                setAbortCallback
            ) => {
                // Upload the smallest file first to block the user the least possible.
                const sortedFiles = Array.from(files).sort((a, b) => a.size - b.size);

                const controller = new AbortController();
                const { signal } = controller;

                let currentXHR = null;
                let addAttachmentRpc = null;

                setAbortCallback?.(() => {
                    controller.abort();
                    addAttachmentRpc?.abort?.();
                    currentXHR?.abort?.();
                });

                for (const file of sortedFiles) {
                    if (signal.aborted) {
                        return;
                    }

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
                    if (signal.aborted) {
                        break;
                    }

                    const file = progressToast.files[sortedFile.progressToastId];
                    let dataURL;
                    try {
                        dataURL = await getDataURLFromFile(sortedFile);
                        if (signal.aborted) {
                            break;
                        }
                    } catch {
                        deleteFile(file.id);
                        env.services.notification.add(
                            _t('Could not load the file "%s".', sortedFile.name),
                            { type: "danger" }
                        );
                        continue;
                    }

                    currentXHR = new XMLHttpRequest();
                    addAttachmentRpc = null;

                    const onProgress = (ev) => {
                        if (ev.lengthComputable) {
                            file.progress = (ev.loaded / ev.total) * 100;
                        }
                    };
                    const onLoad = () => (file.progress = 100);

                    currentXHR.upload.addEventListener("progress", onProgress);
                    currentXHR.upload.addEventListener("load", onLoad);

                    try {
                        addAttachmentRpc = rpc(
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
                            { xhr: currentXHR }
                        );

                        const attachment = await addAttachmentRpc;
                        if (signal.aborted) {
                            break;
                        }

                        if (attachment.error) {
                            file.hasError = true;
                            file.errorMessage = attachment.error;
                        } else {
                            if (attachment.mimetype === "image/webp") {
                                try {
                                    // Generate alternate format for reports.
                                    await convertWebpToJpeg(
                                        dataURL,
                                        file.name,
                                        attachment.id
                                    );
                                } catch (convErr) {
                                    console.warn(
                                        "[uploadService] webp conversion failed:",
                                        convErr
                                    );
                                }
                            }
                            file.uploaded = true;
                            await onUploaded(attachment);
                        }
                    } catch (err) {
                        if (signal.aborted) {
                            break;
                        }
                        file.hasError = true;
                        console.error("Upload error:", err);
                        throw err;
                    } finally {
                        currentXHR.upload.removeEventListener(
                            "progress",
                            onProgress
                        );
                        currentXHR.upload.removeEventListener("load", onLoad);
                        // If there's an error, display the error message for longer
                        const message_autoclose_delay = file.hasError
                            ? AUTOCLOSE_DELAY_LONG
                            : AUTOCLOSE_DELAY;
                        setTimeout(() => deleteFile(file.id), message_autoclose_delay);
                        dataURL = null;
                    }
                }

                currentXHR = null;
                addAttachmentRpc = null;
            },
        };
    },
};

registry.category("services").add("upload", uploadService);
