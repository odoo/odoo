/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { VideoSelector } from "@web_editor/components/media_dialog/video_selector";


export class VideoSelectorDialog extends Component {
    static template = "knowledge.VideoSelectorDialog";
    static components = {
        ...Component.components,
        Dialog,
        VideoSelector,
    };
    static props = {
        ...Component.props,
        save: { type: Function },
        close: { type: Function },
    };

    /**
     * @override
     */
    setup () {
        super.setup();
        this.title = _t("Embed a video");
        this.media = {};
        this.state = useState({
            enableInsertVideoButton: false
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
    selectMedia (media) {
        this.media = media;
        this.state.enableInsertVideoButton = !!this.media.src;
    }

    /**
     * @param {string} error
     */
    errorMessages (error) {
        if (error) {
            console.error(error);
        }
    }

    /**
     * @param {Event} event
     */
    onInsertVideoBtnClick (event) {
        this.props.save(this.media);
        this.props.close();
    }
}
