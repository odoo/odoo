/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from '@web/views/fields/char/char_field';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { humanSize } from "@web/core/utils/binary";
import { useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Override of the FieldChar that will handle the YouTube video upload process.
 *
 * We want to handle the upload from the client browser directly to their YouTube account and avoid
 * that the video file goes through our Odoo server to save time and bandwidth.
 *
 * User selects a file "c:/temp/my_video.mp4", which triggers the upload process directly on the
 * YouTube account they selected on the form view.
 * When the upload is finished, we save the 'youtube_video_id' value in a separate field and keep
 * a "dumb" string as the value of the 'youtube_video' field that will simply contain 'my_video.mp4'.
 *
 * Obviously the usage of this Widget is very limited:
 * - Only works in a form view
 * - Only works along specific other fields in the form view of the social.post model
 *   (youtube_access_token, youtube_video_id, ...)
 *
 * It is not meant to be used anywhere else.
 *
 * The template of the Char field was replaced by a custom one that can display upload buttons and
 * readonly input containing the uploaded file name.
 *
 */
export class YoutubeUploadField extends CharField {
    static template = "social_youtube.YoutubeUploadField";
    setup() {
        super.setup();
        this.fileInputRef = useRef('fileInput');
        this.state = useState({
            uploading: false,
            showSocialYoutubeBar: true,
            socialYoutubeText: _t("Uploading... 0%"),
            uploadProgress: 0,
            uploadErrorMessage: false,
        });
        this.notification = useService("notification");
        this.dialogService = useService("dialog");

        this.useFileAPI = !!window.FileReader;
        this.maxUploadSize = 128 * 1024 * 1024 * 1024; // 128 Go -> max Youtube upload
    }


    /**
     * When the file upload is complete, Youtube triggers its own video "processing"
     * that can take up to a few minutes and during which we can't alter the video
     * in any way nor embed it in the YouTube preview.
     *
     * It's necessary to wait for the process to be complete before letting the user
     * proceed with posting, since we can't alter video properties during this process.
     *
     * So we just periodically ping the API to check the status of this "video processing".
     * When it's done, we resolve the Promise returned by this method.
     *
     * @private
     */
    _awaitPostProcessing(uploadedVideoId) {
        return new Promise((resolve, reject) => {
            this.uploadedVideoId = uploadedVideoId;
            this.videoProcessedResolve = resolve;
            this.processingInfoInterval = setInterval(this._updateProcessingInfo.bind(this), 1500);
        });
    }

    /**
     * Small method that listens to the file upload progress and updates the UI accordingly to give
     * user feedback.
     *
     * @private
     */
    _listenUploadProgress() {
        const xhr = new window.XMLHttpRequest();
        xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
                const roundedProgress = Math.round((e.loaded / e.total) * 100);
                this.state.uploadProgress = roundedProgress;
                this.state.socialYoutubeText = _t('Uploading... %s%', this.state.uploadProgress);
            }
       }, false);

       return xhr;
    }

    /**
     * We use the resumable upload protocol of YouTube to upload our videos, because it allows
     * setting the video as 'private' before uploading it, meaning it will not publicly appear for
     * followers of the channel before the video is actually "posted" on the social application.
     *
     * However, to simplify the implementation, we do not split the video in "chucks" and still
     * upload all at once.
     * Depending on the feedback we get, it would maybe be nice to actually split the file in chunks
     * and implement a "retry" behavior whenever an upload sequence fails.
     *
     * This method will open the upload session and return a 'location' that will be used to upload
     * the file chunks.
     *
     * @param {number} fileSize
     * @param {string} fileType
     * @private
     */
    async _openUploadSession(fileSize, fileType) {
        return new Promise((resolve, reject) => {
            const data = this.props.record.data;
            const title = data.youtube_title;
            const description = data.youtube_description;

            $.ajax({
                url: 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=status%2Csnippet',
                type: 'POST',
                beforeSend: (request) => {
                    request.setRequestHeader("Authorization", "Bearer " + this.props.record.data.youtube_access_token);
                    request.setRequestHeader('Content-Type', 'application/json');
                    request.setRequestHeader("X-Upload-Content-Length", fileSize);
                    request.setRequestHeader("x-Upload-Content-Type", fileType);
                },
                data: JSON.stringify({
                    status: {privacyStatus: "private"},
                    snippet: {
                        title: title,
                        description: description
                    },
                }),
                dataType: 'text',
                processData: false,
                cache: false,
                success: (data, textStatus, request) => {
                    resolve(request.getResponseHeader('location'));
                },
                error: (e) => {
                    if (e.responseText) {
                        const errorReason = JSON.parse(e.responseText).error?.errors[0]?.reason;
                        console.error(errorReason);
                    }
                    this._uploadFailed();
                    reject();
                },
            });
        });
    }

    /**
     * See #_awaitPostProcessing for more information.
     *
     * @private
     */
    _updateProcessingInfo() {
        $.ajax({
            url: 'https://www.googleapis.com/youtube/v3/videos',
            type: 'GET',
            beforeSend: (request) => {
                request.setRequestHeader("Authorization", "Bearer " + this.props.record.data.youtube_access_token);
            },
            data: {
                part: 'processingDetails',
                id: this.uploadedVideoId
            },
            success: (response) => {
                if ('items' in response && response.items.length === 1 && 'processingDetails' in response.items[0]) {
                    var processingDetails = response.items[0].processingDetails;
                    // Youtube is supposed to send a "partsProcessed / partsTotal"
                    // but from my tests it doesn't work (it either doesn't send it or sends 1000 / 1000)
                    this.state.socialYoutubeText = _t('Processing...');

                    if (processingDetails.processingStatus === 'succeeded') {
                        clearInterval(this.processingInfoInterval);
                        this.videoProcessedResolve();
                    }
                } else {
                    this._uploadFailed();
                    this._resetYoutubeVideoValues();
                }
            },
        });
    }
    /**
     * Notify that the upload failed and clear the value of the file input.
     *
     * @private
     */
    _uploadFailed() {
        this.notification.add(_t('Upload failed. Please try again.'), {
            type: 'warning',
        });
        this.fileInputRef.el.value = '';
    }
    /**
     * See #_openUploadSession for more information about the upload process.
     *
     * @param {string} location
     * @param {File} file
     * @private
     */
    async _uploadFile(location, file) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: location,
                type: 'PUT',
                beforeSend: (request) => {
                    request.setRequestHeader("Authorization", "Bearer " + this.props.record.data.youtube_access_token);
                    request.setRequestHeader("Content-Type", 'application/octet-stream');
                },
                success: (response) => {
                    resolve({
                        videoId: response.id,
                        categoryId: response.snippet.categoryId
                    })
                },
                error: () => {
                    this._uploadFailed();
                    reject();
                },
                data: file,
                cache: false,
                contentType: false,
                processData: false,
                xhr: this._listenUploadProgress.bind(this)
            });
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Clear the value and ask the user if they also want to delete the actual
     * video from their YouTube channel.
     *
     * @private
     */
    _onClearClick() {
        this.dialogService.add(ConfirmationDialog, {
            confirmLabel: _t("Yes, delete it"),
            cancelLabel: _t("No"),
            title: _t("Confirmation"),

            body: _t("Do you also want to remove the video from your YouTube account?"),
            confirm: () => {
                $.ajax({
                        url: 'https://www.googleapis.com/youtube/v3/videos',
                        type: 'DELETE',
                        beforeSend: (request) => {
                            request.setRequestHeader("Authorization", "Bearer " + this.props.record.data.youtube_access_token);
                        },
                        data: {
                            id: this.props.record.data.youtube_video_id
                        },
                    });
                    this.uploadedVideoId = null;
                    this._resetYoutubeVideoValues();
            },
            cancel: () => {
                this._resetYoutubeVideoValues();
            },
        });
    }

    _resetYoutubeVideoValues() {
        this.props.record.update({
            youtube_video: false,
            youtube_video_id: false,
            youtube_video_category_id: false,
        });
    }

    /**
     * When the user selects a file:
     * - We start the upload process
     * - Periodically update the UI to show how many % are uploaded
     * - Wait for YouTube post-processing to finish
     * - Change the values of the 'youtube_video_id' and 'youtube_video_category_id' fields when the
     *   upload is complete.
     *
     * @param {Event} e
     * @private
     */
    async _onFileChanged(e) {
        const fileNodes = e.target;
        const hasReadableFile = this.useFileAPI && fileNodes.files.length !== 0;
        const accessToken = this.props.record.data.youtube_access_token;
        if (!accessToken || !hasReadableFile) {
            return;
        }

        const file = fileNodes.files[0];
        if (file.size > this.maxUploadSize) {
            const message = _t(
                "The selected video exceeds the maximum allowed size of %s.",
                humanSize(this.maxUploadSize)
            );
            this.notification.add(message, {
                title: _t("Video Upload"),
                type: 'danger',
            });
            return false;
        }

        this.state.uploading = true;

        const sessionLocation = await this._openUploadSession(file.size, file.type);
        const {videoId, categoryId} = await this._uploadFile(sessionLocation, file);
        await this._awaitPostProcessing(videoId);


        // Strip and keep the last part of file name to get "video.mp4" and not "C:/fakepath/video.mp4".
        const fileName = this.fileInputRef.el.value
            .match(/([^\\.]+)\.\w+$/)[0];

        this.state.uploading = false;
        await this.props.record.update({
            [this.props.name]: fileName,
            youtube_video_id: videoId,
            youtube_video_category_id: categoryId,
        });
    }

    /**
     * Pre-validates the title and description of the video before initiating
     * the upload, So that we can avoid upload failures from YouTube.
     *
     * Some special characters may not have consistent lengths across different encodings.
     * YouTube checks for length using UTF-8 encoding, while JavaScript uses UTF-16.
     * To obtain the correct UTF-8 length, we are destructuring the title and description.
     *
     * @private
     */
    _onUploadClick() {
        const title = this.props.record.data.youtube_title;
        const description = this.props.record.data.youtube_description;
        let message;
        if (!title) {
            message = _t("You need to give your video a title.");
        } else if (!description) {
            message = _t("You need to give your video a description.");
        } else if (
            title.includes("<") ||
            title.includes(">") ||
            description.includes("<") ||
            description.includes(">")
        ) {
            message = _t("You cannot use '>' or '<' in both title and description.");
        } else if ([...title].length > 100) {
            message = _t("Your title cannot exceed 100 characters.");
        } else if ([...description].length > 5000) {
            message = _t("Your description cannot exceed 5000 characters.");
        } else {
            message = false;
        }
        if (message) {
            this.state.uploadErrorMessage = message;
            return;
        }
        this.state.uploadErrorMessage = false;
        this.fileInputRef.el.click();
    }
}

export const youtubeUploadField = {
    ...charField,
    component: YoutubeUploadField,
};

registry.category("fields").add("youtube_upload", youtubeUploadField);
