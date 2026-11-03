import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";
import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { ReadonlyEmbeddedVideoComponent } from "@html_editor/others/embedded_components/core/video/readonly_video";
import { usePositionHook } from "@html_editor/position_hook";
import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUnmount,
    signal,
    t,
    useListener,
    useProps,
} from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class EmbeddedVideoComponent extends ReadonlyEmbeddedVideoComponent {
    static template = "html_editor.EmbeddedVideo";

    videoEmbedProps = useProps({
        host: t.instanceOf(HTMLElement),
        createOverlay: t.function().optional(),
        focusEditable: t.function().optional(),
        commit: t.function().optional(),
        openVideoSelectorDialog: t.function().optional(),
        editable: t.instanceOf(HTMLElement).optional(),
    });

    playerRef = signal.ref();

    setup() {
        super.setup();
        this.videoBlock = this.videoEmbedProps.host;
        this.hasTouch = hasTouch();
        this.state = useEmbeddedState(this.videoBlock);

        if (!this.state.platform || !this.state.videoId) {
            if (!this.props.src) {
                console.error("Video data missing to mount video embedded Component");
                return;
            }
            const videoData = this.getVideoDataFromSrc(this.props.src);
            if (videoData) {
                this.state.platform = videoData.platform;
                this.state.videoId = videoData.videoId;
                this.state.baseUrl = videoData.baseUrl;
                this.state.params = videoData.options;
            } else {
                console.error("Provided src is not a valid url or supported platform");
            }
        }

        this.dropdown = useDropdownState();

        this.videoSettingsOverlay = this.videoEmbedProps.createOverlay(VideoSettings, {
            positionOptions: {
                position: this.hasTouch ? "top-end" : "right-start",
                flip: !this.hasTouch,
            },
            className: "video-overlay",
            closeOnPointerdown: false,
        });

        if (this.hasTouch) {
            onMounted(() => this.openVideoSettings());

            let isScrolling = false;
            const updateVideoSettingsPosition = () => {
                if (isScrolling) {
                    return;
                }
                this.openVideoSettings();
            };
            const onScroll = () => {
                isScrolling = true;
                clearTimeout(this.scrollTimeout);
                // Close menu button on scroll
                this.videoSettingsOverlay.close();
                this.scrollTimeout = setTimeout(() => {
                    isScrolling = false;
                    updateVideoSettingsPosition();
                }, 150);
            };
            useListener(this.videoBlock.ownerDocument, "scroll", onScroll, { capture: true });
            usePositionHook(
                () => this.videoEmbedProps.editable,
                this.videoBlock.ownerDocument,
                updateVideoSettingsPosition
            );
        } else {
            useListener(this.videoBlock, "pointerenter", () => {
                this.openVideoSettings();
            });

            useListener(this.videoBlock, "pointerleave", (e) => {
                if (this.dropdown.isOpen || e.relatedTarget?.closest(".video-overlay")) {
                    return;
                }
                this.videoSettingsOverlay.close();
            });
        }

        onWillDestroy(() => {
            clearTimeout(this.scrollTimeout);
            this.videoSettingsOverlay?.close();
        });
    }

    get embedUrl() {
        const platFormClass = PLATFORMS[this.state.platform];
        return platFormClass.getEmbedUrl(this.state.videoId, this.state.params);
    }

    openVideoSettings() {
        this.videoSettingsOverlay.open({
            target: this.videoBlock,
            props: {
                videoBlock: this.videoBlock,
                ...(!this.hasTouch && {
                    overlay: this.videoSettingsOverlay,
                }),
                replaceVideo: () => {
                    this.videoEmbedProps.openVideoSelectorDialog((media) => {
                        this.replaceVideo(media);
                    }, this.playerRef());
                },
                removeVideo: () => {
                    this.videoBlock.remove();
                    this.videoEmbedProps.commit();
                },
                focusEditable: this.videoEmbedProps.focusEditable,
                dropdown: this.dropdown,
            },
        });
    }

    /**
     * Replace a video in the editor
     * @param {Object} media
     */
    replaceVideo(media) {
        this.state.baseUrl = media.baseUrl;
        this.state.embedUrl = media.embedUrl;
        this.state.platform = media.platform;
        this.state.videoId = media.videoId;
        this.state.params = media.options;
        const isVertical = !!media.options?.isVertical;
        if (isVertical) {
            this.videoBlock.dataset.isVertical = "true";
        } else {
            delete this.videoBlock.dataset.isVertical;
        }
        this.videoBlock.classList.toggle("media_iframe_video_size_for_vertical", isVertical);
        this.videoEmbedProps.focusEditable();
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
    props = useProps({
        videoBlock: t.instanceOf(HTMLElement),
        overlay: t.object().optional(),
        replaceVideo: t.function(),
        removeVideo: t.function(),
        focusEditable: t.function(),
        dropdown: t.object(),
    });

    menuRef = signal.ref();

    setup() {
        this.hasTouch = hasTouch();

        onMounted(() => {
            this.menuRef()?.addEventListener("pointerleave", () => {
                if (this.props.overlay && !this.props.dropdown.isOpen) {
                    this.props.overlay.close();
                }
            });
        });

        useListener(document, "pointerdown", (ev) => {
            if (!this.props.overlay || this.props.dropdown.isOpen) {
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
