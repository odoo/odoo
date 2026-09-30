/* global YT */

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class WebsiteEventTrackLive extends Interaction {
    static selector = ".o_wevent_event_track_live";
    dynamicContent = {
        _root: {
            "t-on-video-ended": this.onVideoEnded,
        },
    };

    setup() {
        this.youtubePlayer = null;
        this.nextSuggestion = null;
        this.outro = null;
        this.setupYoutubePlayer();
    }

    destroy() {
        this.youtubePlayer?.destroy();
        clearInterval(this.timerInterval);
    }

    onPlayerReady() {
        if (this.isDestroyed) {
            return;
        }
        this.el.querySelector(".o_wevent_event_track_live_loading").remove();
    }

    onPlayerStateChange(event) {
        if (this.isDestroyed) {
            return;
        }
        switch (event.data) {
            case YT.PlayerState.ENDED:
                this.triggerEvent("video-ended");
                return;
            case YT.PlayerState.PLAYING:
                this.triggerEvent("video-playing");
                return;
            case YT.PlayerState.PAUSED:
                this.triggerEvent("video-paused");
                return;
        }
    }

    async onVideoEnded() {
        const divEl = document.createElement("div");
        divEl.classList.add("owevent_track_suggestion_loading", "position-absolute", "w-100");
        this.insert(divEl, this.el);
        this.nextSuggestion = await this.waitFor(
            rpc("/event_track/get_track_suggestion", {
                track_id: parseInt(this.el.dataset.trackId),
            })
        );
        this.showSuggestion();
    }

    onReplay() {
        this.youtubePlayer.seekTo(0);
        this.youtubePlayer.playVideo();
        this.el.querySelector(".owevent_track_suggestion_loading").remove();
        if (this.outro) {
            for (const el of this.outro) {
                el.remove();
            }
            delete this.outro;
        }
    }

    triggerEvent(event) {
        this.el.dispatchEvent(new Event(event), { bubbles: true });
    }

    setupYoutubePlayer() {
        const youtubeId = this.el.dataset.youtubeVideoId;
        const youtubeEl = document.createElement("script");
        youtubeEl.src = "https://www.youtube.com/iframe_api";
        this.insert(youtubeEl, document.head);

        window.onYouTubeIframeAPIReady = () => {
            if (this.isDestroyed) {
                return;
            }
            this.youtubePlayer = new YT.Player("o_wevent_youtube_iframe_container", {
                height: "100%",
                width: "100%",
                videoId: youtubeId,
                playerVars: {
                    autoplay: 1,
                    enablejsapi: 1,
                    rel: 0,
                    origin: window.location.origin,
                    widget_referrer: window.location.origin,
                },
                events: {
                    onReady: this.onPlayerReady.bind(this),
                    onStateChange: this.onPlayerStateChange.bind(this),
                },
            });
        };
    }

    /**
     * If a new suggestion has been found, a cover containing a replay button
     * as well as a suggestion will automatically be placed over the Youtube
     * player when the video ends (in non-full screen mode). If no suggestion
     * has been found, the cover will only contain a replay button.
     */
    showSuggestion() {
        if (!this.outro) {
            if (this.nextSuggestion) {
                this.outro = this.renderAt(
                    "website_event_track_live.website_event_track_suggestion",
                    this.nextSuggestion
                );
            } else {
                const data = this.el.dataset;
                this.outro = this.renderAt(
                    "website_event_track_live.website_event_track_replay_suggestion",
                    {
                        current_track: {
                            name: data.trackName,
                            wesite_image_url: data.trackWebsiteImageUrl,
                        },
                    }
                );
            }
            this.addListener(this.outro, "replay", this.onReplay.bind(this));
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event_track_live.WebsiteEventTrackLive", WebsiteEventTrackLive);
