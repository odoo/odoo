/* global YT */
odoo.define('website_event_track_live.website_event_youtube_embed', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var TrackSuggestionWidget = require('website_event_track_live.website_event_track_suggestion');
var ReplaySuggestionWidget = require('website_event_track_live.website_event_track_replay_suggestion');

publicWidget.registry.websiteEventTrackLive = publicWidget.Widget.extend({
    selector: '.o_wevent_event_track_live',
    custom_events: _.extend({}, publicWidget.Widget.prototype.custom_events, {
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
        this.$('.o_wevent_event_track_live_loading').remove();
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
        this.$el.append($('<div/>', {
            class: 'owevent_track_suggestion_loading position-absolute w-100'
        }));
        var self = this;
        this._rpc({
            route: '/event_track/get_track_suggestion',
            params: {
                track_id: this.$el.data('trackId'),
            }
        }).then(function (suggestion) {
            self.nextSuggestion = suggestion;
            self._showSuggestion();
        });
    },

    _onReplay: function () {
        this.youtubePlayer.seekTo(0);
        this.youtubePlayer.playVideo();
        this.$('.owevent_track_suggestion_loading').remove();
        if (this.outro) {
            delete this.outro;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _setupYoutubePlayer: function () {
        var self = this;

        var youtubeId = self.$el.data('youtubeVideoId');
        var $youtubeElement = $('<script/>', {src: 'https://www.youtube.com/iframe_api'});
        $(document.head).append($youtubeElement);

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
                var data = this.$el.data();
                this.outro = new ReplaySuggestionWidget(this, {
                    current_track: {
                        name: data.trackName,
                        website_image_url: data.trackWebsiteImageUrl
                    }
                });
            }
            this.outro.appendTo(this.$el);
            this.outro.on('replay', null, this._onReplay.bind(this));
        }
    }
});

});
