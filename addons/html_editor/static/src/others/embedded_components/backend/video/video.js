import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";
import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { ReadonlyEmbeddedVideoComponent } from "@html_editor/others/embedded_components/core/video/readonly_video";
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

export class EmbeddedVideoComponent extends ReadonlyEmbeddedVideoComponent {
    static template = "html_editor.EmbeddedVideo";

    videoEmbedProps = useProps({
        host: t.instanceOf(HTMLElement),
        createOverlay: t.function().optional(),
        focusEditable: t.function().optional(),
        commit: t.function().optional(),
        openVideoSelectorDialog: t.function().optional(),
    });

    playerRef = signal.ref();

    setup() {
        super.setup();
        this.videoBlock = this.videoEmbedProps.host;
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

        this.videoSettingsOverlay = this.videoEmbedProps.createOverlay(VideoSettings, {
            // Above the video: a full width video leaves no room beside it.
            positionOptions: {
                position: "top-end",
            },
            className: "video-overlay",
            closeOnPointerdown: false,
        });

        useListener(this.videoBlock, "pointerenter", () => {
            this.videoSettingsOverlay.open({
                target: this.videoBlock,
                props: {
                    videoBlock: this.videoBlock,
                    overlay: this.videoSettingsOverlay,
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
                },
            });
        });

        useListener(this.videoBlock, "pointerleave", (e) => {
            if (e.relatedTarget?.closest(".video-overlay")) {
                return;
            }
            this.videoSettingsOverlay.close();
        });

        onWillDestroy(() => {
            this.videoSettingsOverlay?.close();
        });
    }

    get embedUrl() {
        const platFormClass = PLATFORMS[this.state.platform];
        return platFormClass.getEmbedUrl(this.state.videoId, this.state.params);
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
    props = useProps({
        videoBlock: t.instanceOf(HTMLElement),
        overlay: t.object(),
        replaceVideo: t.function(),
        removeVideo: t.function(),
        focusEditable: t.function(),
    });

    menuRef = signal.ref();

    setup() {
        onMounted(() => {
            this.menuRef()?.addEventListener("pointerleave", () => {
                this.props.overlay.close();
            });
        });

        useListener(document, "pointerdown", (ev) => {
            // Let the buttons of the bar receive their click.
            if (this.menuRef()?.contains(ev.target)) {
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
