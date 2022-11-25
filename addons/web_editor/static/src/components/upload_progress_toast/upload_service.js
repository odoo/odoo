/** @odoo-module **/

import { registry } from '@web/core/registry';
import { UploadProgressToast } from './upload_progress_toast';
import { getDataURLFromFile } from 'web.utils';

import { reactive } from "@odoo/owl";

export const AUTOCLOSE_DELAY = 3000;

export const uploadService = {
    dependencies: ['rpc'],
    start(env, { rpc }) {
        let fileId = 0;
        const progressToast = reactive({
            files: {},
            isVisible: false,
        });

        registry.category('main_components').add('UploadProgressToast', {
            Component: UploadProgressToast,
            props: {
                close: () => progressToast.isVisible = false,
            }
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
                const attachment = await rpc('/web_editor/attachment/add_url', {
                    url,
                    'res_model': resModel,
                    'res_id': resId,
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
            uploadFiles: async (files, {resModel, resId, isImage}, onUploaded) => {
                // Upload the smallest file first to block the user the least possible.
                const sortedFiles = Array.from(files).sort((a, b) => a.size - b.size);
                for (const file of sortedFiles) {
                    let fileSize = file.size;
                    if (!fileSize) {
                        fileSize = null;
                    } else if (fileSize < 1024) {
                        fileSize = fileSize.toFixed(2) + " bytes";
                    } else if (fileSize < 1048576) {
                        fileSize = (fileSize / 1024).toFixed(2) + " KB";
                    } else {
                        fileSize = (fileSize / 1048576).toFixed(2) + " MB";
                    }

                    const id = ++fileId;
                    file.progressToastId = id;
                    // This reactive object, built based on the files array,
                    // is given as a prop to the UploadProgressToast.
                    addFile({
                        id,
                        name: file.name,
                        size: fileSize,
                        progress: 0,
                        hasError: false,
                        uploaded: false,
                        errorMessage: '',
                    });
                }

                // Upload one file at a time: no need to parallel as upload is
                // limited by bandwidth.
                for (const sortedFile of sortedFiles) {
                    const file = progressToast.files[sortedFile.progressToastId];
                    const dataURL = await getDataURLFromFile(sortedFile);
                    try {
                        const xhr = new XMLHttpRequest();
                        xhr.upload.addEventListener('progress', ev => {
                            const rpcComplete = ev.loaded / ev.total * 100;
                            file.progress = rpcComplete;
                        });
                        xhr.upload.addEventListener('load', function () {
                            // Don't show yet success as backend code only starts now
                            file.progress = 100;
                        });
                        const attachment = await rpc('/web_editor/attachment/add_data', {
                            'name': file.name,
                            'data': dataURL.split(',')[1],
                            'res_id': resId,
                            'res_model': resModel,
                            'is_image': !!isImage,
                            'width': 0,
                            'quality': 0,
                        }, {xhr});
                        if (attachment.error) {
                            file.hasError = true;
                            file.errorMessage = attachment.error;
                        } else {
                            file.uploaded = true;
                            await onUploaded(attachment);
                        }
                        setTimeout(() => deleteFile(file.id), AUTOCLOSE_DELAY);
                    } catch (error) {
                        file.hasError = true;
                        setTimeout(() => deleteFile(file.id), AUTOCLOSE_DELAY);
                        throw error;
                    }
                }
            }
        };
    },
};

registry.category('services').add('upload', uploadService);
