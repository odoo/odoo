import { registry } from "@web/core/registry";

export const uploadLocalFileService = {
    dependencies: ["upload", "orm"],
    start(env, { upload: uploadService, orm }) {
        const input = document.createElement("input");
        input.type = "file";

        /**
         * Open the system file selector and return the selected files.
         *
         * @param {Object} [options]
         * @param {boolean} [options.multiple=true]
         * @param {string} [options.accept]
         * @returns {Promise<FileList>}
         */
        async function selectLocalFiles({ multiple, accept }) {
            input.multiple = multiple;
            input.accept = accept;
            input.value = ""; // clear previously selected files

            // Open system's file selector
            input.click();

            // Wait for user to select files or cancel.
            await new Promise((resolve) => {
                const resolveAndClear = () => {
                    resolve();
                    input.removeEventListener("change", resolveAndClear);
                    input.removeEventListener("cancel", resolveAndClear);
                };
                // Detect file(s) selected
                input.addEventListener("change", resolveAndClear);
                // Detect file selector closed without selecting files (cancel)
                input.addEventListener("cancel", resolveAndClear);
            });
            return input.files;
        }

        /**
         * @param {FileList} files
         * @param {Object} recordInfo
         * @returns {Promise<Object[]>} attachments
         */
        async function filesToAttachments(files, { resModel, resId }) {
            const attachments = [];
            await uploadService.uploadFiles(files, { resModel, resId }, (attachment) => {
                attachments.push(attachment);
            });
            return attachments;
        }

        /**
         * Open the system file selector and upload the selected files.
         *
         * @param {Object} recordInfo
         * @param {Object} [options]
         * @param {string} [options.accept] Accepted file types
         * @param {boolean} [options.multiple=false] Allow multiple files to be selected
         * @param {boolean} [options.accessToken=false] Add access token to uploaded files
         * @returns {Promise<Object[]>} attachments
         */
        async function upload(
            { resId, resModel },
            { accept = "*/*", multiple = false, accessToken = false } = {}
        ) {
            try {
                const files = await selectLocalFiles({ multiple, accept });
                const attachments = await filesToAttachments(files, { resModel, resId });
                if (accessToken && attachments.length && !attachments[0].public) {
                    await addAccessToken(attachments);
                }
                return attachments;
            } catch {
                // The upload service displays a either a notification or an
                // error message in the progress toast.
                return [];
            }
        }

        /**
         * @param {Object[]} attachments
         * @returns {Promise<Object[]>}
         */
        async function addAccessToken(attachments) {
            const accessTokens = await orm.call("ir.attachment", "generate_access_token", [
                attachments.map((a) => a.id),
            ]);
            attachments.forEach((attachment, index) => {
                attachment.access_token = accessTokens[index];
            });
            return attachments;
        }

        /**
         * @param {Object} attachments
         * @param {Object} [options]
         * @returns {string}
         */
        function getURL(attachment, { unique, download, accessToken } = {}) {
            let url = `/web/content/${attachment.id}`;
            const queryParams = [];
            if (unique) {
                queryParams.push(`unique=${encodeURIComponent(attachment.checksum)}`);
            }
            if (download) {
                queryParams.push("download=true");
            }
            if (accessToken && attachment.access_token) {
                queryParams.push(`access_token=${attachment.access_token}`);
            }
            if (queryParams.length) {
                url += `?${queryParams.join("&")}`;
            }
            return url;
        }

        return { upload, addAccessToken, getURL };
    },
};

registry.category("services").add("uploadLocalFiles", uploadLocalFileService);
