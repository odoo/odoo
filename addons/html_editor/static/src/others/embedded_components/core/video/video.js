import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { getVideoUrl } from "@html_editor/utils/url";
import { Component, onMounted, useExternalListener, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

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
    getProps: (host) => ({ ...getEmbeddedProps(host) }),
};

export class VideoSettings extends Component {
    static template = "html_editor.VideoSettings";
    static components = { Dropdown, DropdownItem };
    static props = {
        replaceVideo: { type: Function },
        removeVideo: { type: Function },
        overlay: { type: Object },
    };

    setup() {
        this.menuRef = useRef("menuRef");
        this.dropdownState = useDropdownState();

        onMounted(() => {
            this.menuRef.el.addEventListener("mouseleave", () => {
                if (!this.dropdownState.isOpen) {
                    this.props.overlay.close();
                }
            });
        });

        useExternalListener(document, "pointerdown", (ev) => {
            if (ev.target.closest(".o-dropdown-item")) {
                return;
            }
            this.props.overlay.close();
        });
    }
}
