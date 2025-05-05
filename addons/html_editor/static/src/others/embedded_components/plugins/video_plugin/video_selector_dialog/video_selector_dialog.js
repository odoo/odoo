import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { Dialog } from "@web/core/dialog/dialog";

import { Component, useState } from "@odoo/owl";

export class VideoSelectorDialog extends Component {
    static template = "html_editor.VideoSelectorDialog";
    static components = { Dialog, VideoSelector };
    static props = {
        save: { type: Function },
        close: { type: Function },
        videoIframe: { type: HTMLElement, optional: true },
    };

    setup() {
        super.setup();
        this.media = {};
        this.state = useState({
            enableInsertVideoButton: false,
        });
    }

    /**
     * Callback function called whenever the video url provided by the user changes.
     * When the video url is empty, the callback function will be called with an
     * empty object ({}) to notify the parent component that the url changes.
     * @param {Object} media
     * @param {string} [media.id]
     * @param {string} [media.src]
     * @param {string} [media.platform]
     * @param {Object} [media.params]
     */
    selectMedia(media) {
        this.media = media;
        this.state.enableInsertVideoButton = !!this.media.src;
    }

    /**
     * @param {Event} event
     */
    onInsertVideoBtnClick(event) {
        this.props.save(this.media);
        this.props.close();
    }
}
