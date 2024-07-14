/** @odoo-module */

import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { Component } from "@odoo/owl";
import { getVideoUrl } from "@knowledge/js/knowledge_utils";


class KnowledgeVideoIframe extends Component {
    static template = "knowledge.VideoIframe";
    static props = {
        src: { type: String },
    };
}

export class VideoBehavior extends AbstractBehavior {
    static template = "knowledge.VideoBehavior";
    static props = {
        ...AbstractBehavior.props,
        platform: { type: String },
        videoId: { type: String },
        params: { type: Object, optional: true },
    };
    static components = {
        VideoIframe: KnowledgeVideoIframe,
    };

    /**
     * @override
     */
    setup () {
        super.setup();
        const url = getVideoUrl(
            this.props.platform,
            this.props.videoId,
            this.props.params
        );
        this.src = url.toString();
    }
}
