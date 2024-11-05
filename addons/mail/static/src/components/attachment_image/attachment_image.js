/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { isMobileOS } from "@web/core/browser/feature_detection";
import core from "web.core";

const { Component, useState } = owl;
const _t = core._t;

class ImageActions extends Component {
    setup() {
        super.setup();
        this.actionsMenuState = useState({
            isOpen: false,
        });
        this.isMobileOS = isMobileOS();
    }

    async setActionsMenuState(state) {
        this.actionsMenuState.isOpen = state.open;
    }
}

Object.assign(ImageActions, {
    props: ["actions", "imagesHeight"],
    template: "mail.ImageActions",
    components: { Dropdown, DropdownItem },
});

registerMessagingComponent(ImageActions);

export class AttachmentImage extends Component {
    /**
     * @returns {AttachmentImage}
     */
    get attachmentImage() {
        return this.props.record;
    }

    getActions(attachmentImage) {
        const res = [];
        if (attachmentImage.attachment.isDeletable) {
            res.push({
                label: _t("Remove"),
                icon: "fa fa-trash",
                class: "o_AttachmentImage_actionUnlink",
                onSelect: (ev) => attachmentImage.onClickUnlink(ev),
            });
        }
        if (attachmentImage.hasDownloadButton) {
            res.push({
                label: _t("Download"),
                icon: "fa fa-download",
                class: "o_AttachmentImage_actionDownload",
                onSelect: (ev) => attachmentImage.onClickDownload(ev),
            });
        }
        return res;
    }
}

Object.assign(AttachmentImage, {
    props: { record: Object, imagesHeight: Number },
    template: "mail.AttachmentImage",
    components: { ImageActions },
});

registerMessagingComponent(AttachmentImage);
