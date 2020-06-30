var onYouTubeIframeAPIReady;

odoo.define('website_event_track.website_event_youtube_embed', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var TrackSuggestionWidget = require('website_event_track.website_event_track_suggestion');

var YOUTUBE_VIDEO_ENDED = 0;
var YOUTUBE_VIDEO_PLAYING = 1;
var YOUTUBE_VIDEO_PAUSED = 2;

publicWidget.registry.websiteEventTrackLive = publicWidget.Widget.extend({
    selector: '.o_wevent_event_track_live',
    custom_events: _.extend({}, publicWidget.Widget.prototype.custom_events, {
        'video-ended': '_onVideoEnded'
    }),

    start: function () {
        var self = this;
        return this._super(...arguments).then(function () {
            self._setupYoutubePlayer();
            self.isFullScreen = !!document.fullscreenElement;
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onPlayerReady: function () {
        $(window).on('resize', this._onResize.bind(this));
    },

    _onPlayerStateChange: function (event) {
        if (event.data === YOUTUBE_VIDEO_ENDED) {
            this.trigger('video-ended');
        } else if (event.data === YOUTUBE_VIDEO_PLAYING) {
            this.trigger('video-playing');
        } else if (event.data === YOUTUBE_VIDEO_PAUSED) {
            this.trigger('video-paused');
        }
    },

    _onVideoEnded: function () {
        var self = this;
        this._rpc({
            route: `/event/track/${this.$el.data('trackId')}/get_track_suggestion`
        }).then(function (suggestion) {
            self.nextSuggestion = suggestion;
            self._showSuggestion();
        });
    },

    /**
     * The 'fullscreenchange' event is probably a better fit but it is unfortunately
     * not triggered when Youtube enters fullscreen mode.
     * However, the global window 'resize' is.
     */
    _onResize: function () {
        this.isFullScreen = !!document.fullscreenElement;
        this._showSuggestion();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _setupYoutubePlayer: function () {
        var self = this;

        var youtubeId = self.$el.data('youtubeVideoId');
        var $youtubeElement = $('<script/>', {src: 'https://www.youtube.com/iframe_api'});
        $(document.head).append($youtubeElement);

        onYouTubeIframeAPIReady = function () {
            new YT.Player('o_wevent_youtube_iframe_container', {
                height: '100%',
                width: '100%',
                videoId: youtubeId,
                playerVars: {
                    autoplay: 1,
                    enablejsapi: 1,
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
     * Automatically launches the next suggested track when this one ends
     * and the user is not in fullscreen mode.
     */
    _showSuggestion: function () {
        if (this.nextSuggestion && !this.isFullScreen) {
            new TrackSuggestionWidget(this, this.nextSuggestion).appendTo(this.$el);
        }
    }
});

});
