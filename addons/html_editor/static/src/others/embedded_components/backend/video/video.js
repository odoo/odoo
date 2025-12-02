import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { getVideoUrl } from "@html_editor/utils/url";
import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUnmount,
    useExternalListener,
    useRef,
} from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ReadonlyEmbeddedVideoComponent } from "../../core/video/readonly_video";

export class EmbeddedVideoComponent extends ReadonlyEmbeddedVideoComponent {
    static template = "html_editor.EmbeddedVideo";
    static props = {
        platform: { type: String },
        videoId: { type: String },
        params: { type: Object, optional: true },
        host: { type: HTMLElement },
        createOverlay: { type: Function, optional: true },
        focusEditable: { type: Function, optional: true },
        addStep: { type: Function, optional: true },
        openVideoSelectorDialog: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.videoBlock = this.props.host;
        this.state = useEmbeddedState(this.videoBlock);
        this.dropdown = useDropdownState();

        this.videoSettingsOverlay = this.props.createOverlay(VideoSettings, {
            positionOptions: {
                position: "right-start",
            },
            className: "video-overlay",
            closeOnPointerdown: false,
        });
        this.iframeRef = useRef("iframeRef");

        useExternalListener(this.videoBlock, "pointerenter", () => {
            this.videoSettingsOverlay.open({
                target: this.videoBlock,
                props: {
                    videoBlock: this.videoBlock,
                    overlay: this.videoSettingsOverlay,
                    replaceVideo: () => {
                        this.props.openVideoSelectorDialog((media) => {
                            this.replaceVideo(media);
                        }, this.iframeRef.el);
                    },
                    removeVideo: () => {
                        this.videoBlock.remove();
                        this.props.addStep();
                    },
                    focusEditable: this.props.focusEditable,
                    dropdown: this.dropdown,
                },
            });
        });

        useExternalListener(this.videoBlock, "pointerleave", (e) => {
            if (this.dropdown.isOpen || e.relatedTarget?.closest(".video-overlay")) {
                return;
            }
            this.videoSettingsOverlay.close();
        });

        onWillDestroy(() => {
            this.videoSettingsOverlay?.close();
        });
    }

    get url() {
        return getVideoUrl(this.state.platform, this.state.videoId, this.state.params).toString();
    }

    /**
     * Replace a video in the editor
     * @param {Object} media
     */
    replaceVideo(media) {
        this.state.videoId = media.videoId;
        this.state.platform = media.platform;
        this.state.params = media.params;
        this.props.focusEditable();
    }
}

export const videoEmbedding = {
    name: "video",
    Component: EmbeddedVideoComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};

export class VideoSettings extends Component {
    static template = "html_editor.VideoSettings";
    static components = { Dropdown, DropdownItem };
    static props = {
        videoBlock: { type: HTMLElement },
        overlay: { type: Object },
        replaceVideo: { type: Function },
        removeVideo: { type: Function },
        focusEditable: { type: Function },
        dropdown: { type: Object },
    };

    setup() {
        this.menuRef = useRef("menuRef");

        onMounted(() => {
            this.menuRef.el.addEventListener("pointerleave", () => {
                if (!this.props.dropdown.isOpen) {
                    this.props.overlay.close();
                }
            });
        });

        useExternalListener(document, "pointerdown", (ev) => {
            if (this.props.dropdown.isOpen) {
                return;
            }
            this.props.overlay.close();
        });

        onWillUnmount(() => {
            if (!this.props.videoBlock.isConnected) {
                this.props.focusEditable();
            }
        });
    }
}
