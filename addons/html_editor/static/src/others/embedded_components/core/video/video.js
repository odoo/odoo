import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { getVideoUrl } from "@html_editor/utils/url";
import { Component } from "@odoo/owl";

export class EmbeddedVideoIframe extends Component {
    static template = "html_editor.EmbeddedVideoIframe";
    static props = {
        src: { type: String },
    };
}

export class EmbeddedVideoComponent extends Component {
    static template = "html_editor.EmbeddedVideo";
    static props = {
        platform: { type: String },
        videoId: { type: String },
        params: { type: Object, optional: true },
    };
    static components = { VideoIframe: EmbeddedVideoIframe };

    setup() {
        super.setup();
        const url = getVideoUrl(this.props.platform, this.props.videoId, this.props.params);
        this.src = url.toString();
    }
}

export const videoEmbedding = {
    name: "video",
    Component: EmbeddedVideoComponent,
    getProps: (host) => {
        return { ...getEmbeddedProps(host) };
    },
};
