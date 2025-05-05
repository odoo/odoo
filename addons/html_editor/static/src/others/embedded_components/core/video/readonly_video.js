import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { getVideoUrl } from "@html_editor/utils/url";
import { Component } from "@odoo/owl";

export class ReadonlyEmbeddedVideoComponent extends Component {
    static template = "html_editor.EmbeddedVideo";
    static props = {
        platform: { type: String },
        videoId: { type: String },
        params: { type: Object, optional: true },
    };

    get url() {
        return getVideoUrl(this.props.platform, this.props.videoId, this.props.params).toString();
    }
}

export const readonlyVideoEmbedding = {
    name: "video",
    Component: ReadonlyEmbeddedVideoComponent,
    getProps: (host) => ({ ...getEmbeddedProps(host) }),
};
