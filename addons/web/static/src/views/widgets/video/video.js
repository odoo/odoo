import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class VideoDialog extends Component {
    static components = { Dialog };
    static template = "web.VideoDialog";
    props = useProps({
        url: t.string(),
        title: t.string(),
        close: t.function(),
    });
}

/**
 * Displays a preview image of a video, which opens the video in a dialog when
 * clicked. Usage: <widget name="video" preview="/module/static/img/preview.webp"
 * url="https://www.youtube.com/embed/..." title="..."/>
 */
export class VideoWidget extends Component {
    static template = "web.VideoWidget";
    props = useProps({
        preview: t.string(),
        url: t.string(),
        title: t.string().optional(),
    });

    setup() {
        this.dialog = useService("dialog");
    }

    get title() {
        return this.props.title || _t("Video");
    }

    openVideo() {
        this.dialog.add(VideoDialog, { url: this.props.url, title: this.title });
    }
}

export const videoWidget = {
    component: VideoWidget,
    extractProps: ({ attrs }) => ({
        preview: attrs.preview,
        url: attrs.url,
        title: attrs.title,
    }),
};

registry.category("view_widgets").add("video", videoWidget);
