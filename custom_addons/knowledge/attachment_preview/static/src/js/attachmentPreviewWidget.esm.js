import {Component, onWillStart, useRef, useState} from "@odoo/owl";
import {ensureJQuery} from "@web/core/ensure_jquery";
import {sprintf} from "@web/core/utils/strings";

export class AttachmentPreviewWidget extends Component {
    static template = "attachment_preview.AttachmentPreviewWidget";
    static props = {};
    setup() {
        super.setup();
        Component.env.bus.addEventListener(
            "open_attachment_preview",
            ({detail: {attachment_id, attachment_info_list}}) =>
                this._onAttachmentPreview(attachment_id, attachment_info_list)
        );
        Component.env.bus.addEventListener("hide_attachment_preview", this.hide);
        this.state = useState({activeIndex: 0});
        this.currentRef = useRef("current");
        this.iframeRef = useRef("iframe");
        onWillStart(async () => {
            await ensureJQuery();
        });
    }

    _onCloseClick() {
        this.hide();
    }

    _onPreviousClick() {
        this.previous();
    }

    _onNextClick() {
        this.next();
    }

    _onPopoutClick() {
        if (!this.attachments[this.state.activeIndex]) return;
        // eslint-disable-next-line no-undef
        window.open(this.attachments[this.state.activeIndex].previewUrl);
    }

    next() {
        var index = this.state.activeIndex + 1;
        if (index >= this.attachments.length) {
            index = 0;
        }
        this.state.activeIndex = index;
        this.updatePaginator();
        this.loadPreview();
    }

    previous() {
        var index = this.state.activeIndex - 1;
        if (index < 0) {
            index = this.attachments.length - 1;
        }
        this.state.activeIndex = index;
        this.updatePaginator();
        this.loadPreview();
    }

    show() {
        $(".attachment_preview_widget").removeClass("d-none");
    }

    hide() {
        $(".attachment_preview_widget").addClass("d-none");
    }

    updatePaginator() {
        var value = sprintf(
            "%s / %s",
            this.state.activeIndex + 1,
            this.attachments.length
        );
        $(this.currentRef.el).html(value);
    }

    loadPreview() {
        if (this.attachments.length === 0) {
            $(this.iframeRef.el).attr("src", "about:blank");
            return;
        }
        var att = this.attachments[this.state.activeIndex];
        $(this.iframeRef.el).attr("src", att.previewUrl);
    }

    setAttachments(attachments, active_attachment_id) {
        this.attachments = attachments;
        if (!attachments) return;
        for (let i = 0; i < attachments.length; ++i) {
            if (parseInt(attachments[i].id, 10) === active_attachment_id) {
                this.state.activeIndex = i;
            }
        }
        this.updatePaginator();
        this.loadPreview();
    }

    _onAttachmentPreview(attachment_id, attachment_info_list) {
        this.setAttachments(attachment_info_list, attachment_id);
        this.show();
    }
}
