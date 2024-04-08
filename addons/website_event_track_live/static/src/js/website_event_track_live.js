/** @odoo-module **/
/* global YT */

import publicWidget from "@web/legacy/js/public/public_widget";
import TrackSuggestionWidget from "@website_event_track_live/js/website_event_track_suggestion";
import ReplaySuggestionWidget from "@website_event_track_live/js/website_event_track_replay_suggestion";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteEventTrackLive = publicWidget.Widget.extend({
    selector: '.o_wevent_event_track_live',
    custom_events: Object.assign({}, publicWidget.Widget.prototype.custom_events, {
        'video-ended': '_onVideoEnded'
    }),

    start: function () {
        var self = this;
        return this._super(...arguments).then(function () {
            self._setupYoutubePlayer();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onPlayerReady: function () {
        document.querySelector('.o_wevent_event_track_live_loading').remove();
    },

    _onPlayerStateChange: function (event) {
        switch (event.data) {
            case YT.PlayerState.ENDED:
                this.trigger('video-ended');
                return;
            case YT.PlayerState.PLAYING:
                this.trigger('video-playing');
                return;
            case YT.PlayerState.PAUSED:
                this.trigger('video-paused');
                return;
        };
    },

    _onVideoEnded: function () {
        this.el.insertAdjacentHTML('beforeend', '<div class="owevent_track_suggestion_loading position-absolute w-100"></div>');
        var self = this;
        rpc('/event_track/get_track_suggestion', {
            track_id: this.el.dataset.trackId,
        }).then(function (suggestion) {
            self.nextSuggestion = suggestion;
            self._showSuggestion();
        });
    },

    _onReplay: function () {
        this.youtubePlayer.seekTo(0);
        this.youtubePlayer.playVideo();
        document.querySelector('.owevent_track_suggestion_loading').remove();
        if (this.outro) {
            delete this.outro;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _setupYoutubePlayer: function () {
        var self = this;

        const youtubeId = self.el.dataset.youtubeVideoId;
        const youtubeElement = document.createElement('script');
        youtubeElement.src = 'https://www.youtube.com/iframe_api';
        document.head.appendChild(youtubeElement);

        window.onYouTubeIframeAPIReady = function () {
            self.youtubePlayer = new YT.Player('o_wevent_youtube_iframe_container', {
                height: '100%',
                width: '100%',
                videoId: youtubeId,
                playerVars: {
                    autoplay: 1,
                    enablejsapi: 1,
                    rel: 0,
                    origin: window.location.origin,
                    widget_referrer: window.location.origin,
                },
                events: {
                    'onReady': self._onPlayerReady.bind(self),
                    'onStateChange': self._onPlayerStateChange.bind(self)
                }
            });
        };
    },

    /**
     * If a new suggestion has been found, a cover containing a replay button
     * as well as a suggestion will automatically be placed over the Youtube
     * player when the video ends (in non-full screen mode). If no suggestion
     * has been found, the cover will only contain a replay button.
     */
    _showSuggestion: function () {
        if (!this.outro) {
            if (this.nextSuggestion) {
                this.outro = new TrackSuggestionWidget(this, this.nextSuggestion);
            } else {
                const data = this.el.dataset;
                this.outro = new ReplaySuggestionWidget(this, {
                    current_track: {
                        name: data.trackName,
                        website_image_url: data.trackWebsiteImageUrl
                    }
                });
            }
            this.el.appendChild(this.outro.el);
            this.outro.on('replay', null, this._onReplay.bind(this));
        }
    }
});
