/** @odoo-module */

import { Component, xml } from "@odoo/owl";
import { endKnowledgeTour, openCommandBar } from "../knowledge_tour_utils.js";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { VideoBehavior } from "@knowledge/components/behaviors/video_behavior/video_behavior";
import { VideoSelector } from "@web_editor/components/media_dialog/video_selector";

const YoutubeVideoId = "Rk1MYMPDx3s";
let unpatchVideoBehavior;
let unpatchVideoSelector;

class MockedVideoIframe extends Component {
    static template = xml`
        <div class="o_video_iframe_src" t-out="props.src" />
    `;
};

registry.category("web_tour.tours").add("knowledge_video_command_tour", {
    url: "/web",
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(), { // open the Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        }, { // patch the components
            trigger: "body",
            run: () => {
                unpatchVideoBehavior = patch(VideoBehavior.components, {
                    ...VideoBehavior.components,
                    VideoIframe: MockedVideoIframe
                });
                unpatchVideoSelector = patch(VideoSelector.components, {
                    ...VideoSelector.components,
                    VideoIframe: MockedVideoIframe
                });
            },
        }, { // open the command bar
            trigger: ".odoo-editor-editable > p",
            run: function () {
                openCommandBar(this.$anchor[0]);
            },
        }, { // click on the /video command
            trigger: '.oe-powerbox-commandName:contains("Video")',
            run: "click",
        }, {
            content: "Enter a video URL",
            trigger: ".modal-body #o_video_text",
            run: `text https://www.youtube.com/watch?v=${YoutubeVideoId}`,
        }, {
            content: "Wait for preview to appear",
            trigger: `.o_video_iframe_src:contains("//www.youtube.com/embed/${YoutubeVideoId}?rel=0&autoplay=0")`,
            run: () => {},
        }, {
            content: "Confirm selection",
            trigger: '.modal-footer button:contains("Insert Video")',
        }, { // wait for the block to appear in the editor
            trigger: ".o_knowledge_behavior_type_video",
            extra_trigger: `.o_knowledge_behavior_type_video .o_video_iframe_src:contains("https://www.youtube.com/embed/${YoutubeVideoId}?rel=0&autoplay=0")`
        }, { // unpatch the components
            trigger: "body",
            run: () => {
                unpatchVideoBehavior();
                unpatchVideoSelector();
            },
        },...endKnowledgeTour()
    ]
});
