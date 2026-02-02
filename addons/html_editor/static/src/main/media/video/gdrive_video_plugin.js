import { _t } from "@web/core/l10n/translation";
import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export const GDRIVE_URL_GET_VIDEO_ID =
    /^https:\/\/drive\.google\.com\/file\/d\/(.*?)\/.*?(?:\?[0-9a-z_\-=&]+)?$/i;

export class GDriveVideoPlugin extends ThirdPartyVideoAbstract {
    static id = "gDriveVideo";

    /**
     * @param {string} url
     */
    getCommandForVideoUrlPaste(url) {
        const videoUrl = GDRIVE_URL_GET_VIDEO_ID.exec(url);
        if (videoUrl) {
            // URL is a Google Drive file.

            return {
                title: _t("Embed Google Drive Video"), // TODO  maybe we should embed any kind of public file ?
                description: _t("Embed the video in the document."),
                icon: "fa-play-circle",
                run: () => this.insertVideoElement(videoUrl[0]),
            };
        }
    }
}
