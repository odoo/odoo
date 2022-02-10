/** @odoo-module **/

import { registry } from '@web/core/registry';
import { UploadProgressToast } from './upload_progress_toast';
import { getDataURLFromFile } from 'web.utils';

const { reactive } = owl;

const AUTOCLOSE_DELAY = 3000;

export const uploadService = {
    dependencies: ['rpc'],
    start(env, { rpc }) {
        let fileId = 0;
        const filesToUpload = reactive({});

        registry.category('main_components').add('UploadProgressToast', {
            Component: UploadProgressToast,
            props: { files: filesToUpload },
        });

        return {
            uploadUrl: async (url, { resModel, resId }, onUploaded) => {
                const attachment = await rpc('/web_editor/attachment/add_url', {
                    url,
                    'res_model': resModel,
                    'res_id': resId,
                });
                await onUploaded(attachment);
            },

            uploadFiles: async (files, {resModel, resId, isImage}, onUploaded) => {
                // Upload the smallest file first to block the user the least possible.
                for (const [index, file] of Array.from(files).sort((a, b) => a.size - b.size).entries()) {
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
                    filesToUpload[id] = {
                        id,
                        index,
                        name: file.name,
                        size: fileSize,
                        progress: 0,
                        hasError: false,
                        uploaded: false,
                        errorMessage: '',
                    };
                }

                await Promise.all(Object.keys(filesToUpload).map(async (fileId, index) => {
                    const file = filesToUpload[fileId];
                    const dataURL = await getDataURLFromFile(files[index]);
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
                        setTimeout(() => delete filesToUpload[file.id], AUTOCLOSE_DELAY);
                    } catch (error) {
                        file.hasError = true;
                        setTimeout(() => delete filesToUpload[file.id], AUTOCLOSE_DELAY);
                        throw error;
                    }
                }));
            }
        };
    },
};

registry.category('services').add('upload', uploadService);
