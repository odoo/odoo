import { reactive } from "@odoo/owl";
import { checkFileSize } from "@web/core/utils/files";
import { humanNumber } from "@web/core/utils/numbers";

export const fileProgressBar = reactive({
    files: {},
    uploadInProgress: false,
    isVisible: false,
    cancelAllUpload: false,
    multipleFiles: false,
    totalFilesCount: 0,
});

// Utility methods to manage fileProgressBar
export const fileProgressManager = {
    addFile(file) {
        if (file.name && !fileProgressBar.files[file.id]) {
            fileProgressBar.files[file.id] = file;
            fileProgressBar.isVisible = true;
        }
    },

    calculateTime(startTime, ev) {
        const elapsedTime = (Date.now() - startTime) / 1000;
        const totalUploadTime = (elapsedTime / ev.loaded) * ev.total;
        return Math.max(totalUploadTime - elapsedTime, 0);
    },

    clearUploadedFiles() {
        for (const [fileId, file] of Object.entries(fileProgressBar.files)) {
            if (file.uploaded) {
                setTimeout(() => {
                    delete fileProgressBar.files[fileId];
                    if (Object.keys(fileProgressBar.files).length === 0) {
                        fileProgressBar.isVisible = false;
                        fileProgressBar.totalFilesCount = 0;
                    }
                }, 2000);
            }
        }
    },

    fileUploadLoaded(filesToUpload) {
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
    },

    fileInError(filesToUpload) {
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
    },

    isCancelAllUpload(fileId) {
        if (fileProgressBar.cancelAllUpload) {
            delete fileProgressBar.files[fileId];
            fileProgressBar.isVisible = false;
            fileProgressBar.cancelAllUpload = false;
            fileProgressBar.totalFilesCount = 0;
            return true;
        }
        return false;
    },

    prepareFile(sortedFiles, notificationService, fileId) {
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
            fileProgressManager.addFile(fileDetails);
        }
        return fileId;
    },

    remainingTime(fileDetails, remainingTime) {
        fileDetails.remainingTime = `${Math.floor(remainingTime / 60)}m:${Math.round(
            remainingTime % 60
        )}s`;
    },

    uploadInProgress(filesToUpload, remainingTime, ev) {
        if (filesToUpload) {
            Object.values(filesToUpload).forEach((file) => {
                if (file.progressToastId) {
                    const fileDetails = fileProgressBar.files[file.progressToastId];
                    if (fileDetails) {
                        fileDetails.progress = (ev.loaded / ev.total) * 100;
                        fileProgressManager.remainingTime(fileDetails, remainingTime);
                        fileDetails.cancel_upload = false;
                    }
                }
            });
        }
    },
};
