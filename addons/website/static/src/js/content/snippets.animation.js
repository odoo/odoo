odoo.define('website.content.snippets.animation', function (require) {
'use strict';

/**
 * Provides a way to start JS code for snippets' initialization and animations.
 */

var Class = require('web.Class');
var core = require('web.core');
var mixins = require('web.mixins');
var utils = require('web.utils');
var publicWidget = require('web.public.widget');

var qweb = core.qweb;

// Initialize fallbacks for the use of requestAnimationFrame,
// cancelAnimationFrame and performance.now()
window.requestAnimationFrame = window.requestAnimationFrame
    || window.webkitRequestAnimationFrame
    || window.mozRequestAnimationFrame
    || window.msRequestAnimationFrame
    || window.oRequestAnimationFrame;
window.cancelAnimationFrame = window.cancelAnimationFrame
    || window.webkitCancelAnimationFrame
    || window.mozCancelAnimationFrame
    || window.msCancelAnimationFrame
    || window.oCancelAnimationFrame;
if (!window.performance || !window.performance.now) {
    window.performance = {
        now: function () {
            return Date.now();
        }
    };
}

/**
 * Add the notion of edit mode to public widgets.
 */
publicWidget.Widget.include({
    /**
     * Indicates if the widget should not be instantiated in edit. The default
     * is true, indeed most (all?) defined widgets only want to initialize
     * events and states which should not be active in edit mode (this is
     * especially true for non-website widgets).
     *
     * @type {boolean}
     */
    disabledInEditableMode: true,
    /**
     * Acts as @see Widget.events except that the events are only binded if the
     * Widget instance is instanciated in edit mode. The property is not
     * considered if @see disabledInEditableMode is false.
     */
    edit_events: null,
    /**
     * Acts as @see Widget.events except that the events are only binded if the
     * Widget instance is instanciated in readonly mode. The property only
     * makes sense if @see disabledInEditableMode is false, you should simply
     * use @see Widget.events otherwise.
     */
    read_events: null,

    /**
     * Initializes the events that will need to be binded according to the
     * given mode.
     *
     * @constructor
     * @param {Object} parent
     * @param {Object} [options]
     * @param {boolean} [options.editableMode=false]
     *        true if the page is in edition mode
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.editableMode = this.options.editableMode || false;
        var extraEvents = this.editableMode ? this.edit_events : this.read_events;
        if (extraEvents) {
            this.events = _.extend(this.events || {}, extraEvents);
        }
    },
});

/**
 * In charge of handling one animation loop using the requestAnimationFrame
 * feature. This is used by the `Animation` class below and should not be called
 * directly by an end developer.
 *
 * This uses a simple API: it can be started, stopped, played and paused.
 */
var AnimationEffect = Class.extend(mixins.ParentedMixin, {
    /**
     * @constructor
     * @param {Object} parent
     * @param {function} updateCallback - the animation update callback
     * @param {string} [startEvents=scroll]
     *        space separated list of events which starts the animation loop
     * @param {jQuery|DOMElement} [$startTarget=window]
     *        the element(s) on which the startEvents are listened
     * @param {Object} [options]
     * @param {function} [options.getStateCallback]
     *        a function which returns a value which represents the state of the
     *        animation, i.e. for two same value, no refreshing of the animation
     *        is needed. Can be used for optimization. If the $startTarget is
     *        the window element, this defaults to returning the current
     *        scoll offset of the window or the size of the window for the
     *        scroll and resize events respectively.
     * @param {string} [options.endEvents]
     *        space separated list of events which pause the animation loop. If
     *        not given, the animation is stopped after a while (if no
     *        startEvents is received again)
     * @param {jQuery|DOMElement} [options.$endTarget=$startTarget]
     *        the element(s) on which the endEvents are listened
     */
    init: function (parent, updateCallback, startEvents, $startTarget, options) {
        mixins.ParentedMixin.init.call(this);
        this.setParent(parent);

        options = options || {};
        this._minFrameTime = 1000 / (options.maxFPS || 100);

        // Initialize the animation startEvents, startTarget, endEvents, endTarget and callbacks
        this._updateCallback = updateCallback;
        this.startEvents = startEvents || 'scroll';
        this.$startTarget = $($startTarget || window);
        if (options.getStateCallback) {
            this._getStateCallback = options.getStateCallback;
        } else if (this.startEvents === 'scroll' && this.$startTarget[0] === window) {
            this._getStateCallback = function () {
                return window.pageYOffset;
            };
        } else if (this.startEvents === 'resize' && this.$startTarget[0] === window) {
            this._getStateCallback = function () {
                return {
                    width: window.innerWidth,
                    height: window.innerHeight,
                };
            };
        } else {
            this._getStateCallback = function () {
                return undefined;
            };
        }
        this.endEvents = options.endEvents || false;
        this.$endTarget = options.$endTarget ? $(options.$endTarget) : this.$startTarget;

        this._updateCallback = this._updateCallback.bind(parent);
        this._getStateCallback = this._getStateCallback.bind(parent);

        // Add a namespace to events using the generated uid
        this._uid = '_animationEffect' + _.uniqueId();
        this.startEvents = _processEvents(this.startEvents, this._uid);
        if (this.endEvents) {
            this.endEvents = _processEvents(this.endEvents, this._uid);
        }

        function _processEvents(events, namespace) {
            events = events.split(' ');
            return _.each(events, function (e, index) {
                events[index] += ('.' + namespace);
            }).join(' ');
        }
    },
    /**
     * @override
     */
    destroy: function () {
        mixins.ParentedMixin.destroy.call(this);
        this.stop();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Initializes when the animation must be played and paused and initializes
     * the animation first frame.
     */
    start: function () {
        // Initialize the animation first frame
        this._paused = false;
        this._rafID = window.requestAnimationFrame((function (t) {
            this._update(t);
            this._paused = true;
        }).bind(this));

        // Initialize the animation play/pause events
        if (this.endEvents) {
            /**
             * If there are endEvents, the animation should begin playing when
             * the startEvents are triggered on the $startTarget and pause when
             * the endEvents are triggered on the $endTarget.
             */
            this.$startTarget.on(this.startEvents, (function (e) {
                if (this._paused) {
                    _.defer(this.play.bind(this, e));
                }
            }).bind(this));
            this.$endTarget.on(this.endEvents, (function () {
                if (!this._paused) {
                    _.defer(this.pause.bind(this));
                }
            }).bind(this));
        } else {
            /**
             * Else, if there is no endEvents, the animation should begin playing
             * when the startEvents are *continuously* triggered on the
             * $startTarget or fully played once. To achieve this, the animation
             * begins playing and is scheduled to pause after 2 seconds. If the
             * startEvents are triggered during that time, this is not paused
             * for another 2 seconds. This allows to describe an "effect"
             * animation (which lasts less than 2 seconds) or an animation which
             * must be playing *during* an event (scroll, mousemove, resize,
             * repeated clicks, ...).
             */
            var pauseTimer = null;
            this.$startTarget.on(this.startEvents, _.throttle((function (e) {
                this.play(e);

                clearTimeout(pauseTimer);
                pauseTimer = _.delay((function () {
                    this.pause();
                    pauseTimer = null;
                }).bind(this), 2000);
            }).bind(this), 250, {trailing: false}));
        }
    },
    /**
     * Pauses the animation and destroys the attached events which trigger the
     * animation to be played or paused.
     */
    stop: function () {
        this.$startTarget.off(this.startEvents);
        if (this.endEvents) {
            this.$endTarget.off(this.endEvents);
        }
        this.pause();
    },
    /**
     * Forces the requestAnimationFrame loop to start.
     *
     * @param {Event} e - the event which triggered the animation to play
     */
    play: function (e) {
        this._newEvent = e;
        if (!this._paused) {
            return;
        }
        this._paused = false;
        this._rafID = window.requestAnimationFrame(this._update.bind(this));
        this._lastUpdateTimestamp = undefined;
    },
    /**
     * Forces the requestAnimationFrame loop to stop.
     */
    pause: function () {
        if (this._paused) {
            return;
        }
        this._paused = true;
        window.cancelAnimationFrame(this._rafID);
        this._lastUpdateTimestamp = undefined;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Callback which is repeatedly called by the requestAnimationFrame loop.
     * It controls the max fps at which the animation is running and initializes
     * the values that the update callback needs to describe the animation
     * (state, elapsedTime, triggered event).
     *
     * @private
     * @param {DOMHighResTimeStamp} timestamp
     */
    _update: function (timestamp) {
        if (this._paused) {
            return;
        }
        this._rafID = window.requestAnimationFrame(this._update.bind(this));

        // Check the elapsed time since the last update callback call.
        // Consider it 0 if there is no info of last timestamp and leave this
        // _update call if it was called too soon (would overflow the set max FPS).
        var elapsedTime = 0;
        if (this._lastUpdateTimestamp) {
            elapsedTime = timestamp - this._lastUpdateTimestamp;
            if (elapsedTime < this._minFrameTime) {
                return;
            }
        }

        // Check the new animation state thanks to the get state callback and
        // store its new value. If the state is the same as the previous one,
        // leave this _update call, except if there is an event which triggered
        // the "play" method again.
        var animationState = this._getStateCallback(elapsedTime, this._newEvent);
        if (!this._newEvent
         && animationState !== undefined
         && _.isEqual(animationState, this._animationLastState)) {
            return;
        }
        this._animationLastState = animationState;

        // Call the update callback with frame parameters
        this._updateCallback(this._animationLastState, elapsedTime, this._newEvent);
        this._lastUpdateTimestamp = timestamp; // Save the timestamp at which the update callback was really called
        this._newEvent = undefined; // Forget the event which triggered the last "play" call
    },
});

/**
 * Also register AnimationEffect automatically (@see effects, _prepareEffects).
 */
var Animation = publicWidget.Widget.extend({
    /**
     * The max FPS at which all the automatic animation effects will be
     * running by default.
     */
    maxFPS: 100,
    /**
     * @see this._prepareEffects
     *
     * @type {Object[]}
     * @type {string} startEvents
     *       The names of the events which trigger the effect to begin playing.
     * @type {string} [startTarget]
     *       A selector to find the target where to listen for the start events
     *       (if no selector, the window target will be used). If the whole
     *       $target of the animation should be used, use the 'selector' string.
     * @type {string} [endEvents]
     *       The name of the events which trigger the end of the effect (if none
     *       is defined, the animation will stop after a while
     *       @see AnimationEffect.start).
     * @type {string} [endTarget]
     *       A selector to find the target where to listen for the end events
     *       (if no selector, the startTarget will be used). If the whole
     *       $target of the animation should be used, use the 'selector' string.
     * @type {string} update
     *       A string which refers to a method which will be used as the update
     *       callback for the effect. It receives 3 arguments: the animation
     *       state, the elapsedTime since last update and the event which
     *       triggered the animation (undefined if just a new update call
     *       without trigger).
     * @type {string} [getState]
     *       The animation state is undefined by default, the scroll offset for
     *       the particular {startEvents: 'scroll'} effect and an object with
     *       width and height for the particular {startEvents: 'resize'} effect.
     *       There is the possibility to define the getState callback of the
     *       animation effect with this key. This allows to improve performance
     *       even further in some cases.
     */
    effects: [],

    /**
     * Initializes the animation. The method should not be called directly as
     * called automatically on animation instantiation and on restart.
     *
     * Also, prepares animation's effects and start them if any.
     *
     * @override
     */
    start: function () {
        this._prepareEffects();
        _.each(this._animationEffects, function (effect) {
            effect.start();
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Registers `AnimationEffect` instances.
     *
     * This can be done by extending this method and calling the @see _addEffect
     * method in it or, better, by filling the @see effects property.
     *
     * @private
     */
    _prepareEffects: function () {
        this._animationEffects = [];

        var self = this;
        _.each(this.effects, function (desc) {
            self._addEffect(self[desc.update], desc.startEvents, _findTarget(desc.startTarget), {
                getStateCallback: desc.getState && self[desc.getState],
                endEvents: desc.endEvents || undefined,
                $endTarget: _findTarget(desc.endTarget),
                maxFPS: self.maxFPS,
            });

            // Return the DOM element matching the selector in the form
            // described above.
            function _findTarget(selector) {
                if (selector) {
                    if (selector === 'selector') {
                        return self.$target;
                    }
                    return self.$(selector);
                }
                return undefined;
            }
        });
    },
    /**
     * Registers a new `AnimationEffect` according to given parameters.
     *
     * @private
     * @see AnimationEffect.init
     */
    _addEffect: function (updateCallback, startEvents, $startTarget, options) {
        this._animationEffects.push(
            new AnimationEffect(this, updateCallback, startEvents, $startTarget, options)
        );
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

var registry = publicWidget.registry;

registry.slider = publicWidget.Widget.extend({
    selector: '.carousel',
    disabledInEditableMode: false,
    edit_events: {
        'slid.bs.carousel': '_onEditionSlide',
    },

    /**
     * @override
     */
    start: function () {
        if (!this.editableMode) {
            this.$('img').on('load.slider', this._onImageLoaded.bind(this));
            this._computeHeights();
        }
        this.$target.carousel();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$('img').off('.slider');
        this.$target.carousel('pause');
        this.$target.removeData('bs.carousel');
        _.each(this.$('.carousel-item'), function (el) {
            $(el).css('min-height', '');
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _computeHeights: function () {
        var maxHeight = 0;
        var $items = this.$('.carousel-item');
        _.each($items, function (el) {
            var $item = $(el);
            var isActive = $item.hasClass('active');
            $item.addClass('active');
            var height = $item.outerHeight();
            if (height > maxHeight) {
                maxHeight = height;
            }
            $item.toggleClass('active', isActive);
        });
        _.each($items, function (el) {
            $(el).css('min-height', maxHeight);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onEditionSlide: function () {
        this._computeHeights();
    },
    /**
     * @private
     */
    _onImageLoaded: function () {
        this._computeHeights();
    },
});

registry.backgroundVideo = Animation.extend({
    selector: '.o_video_background',
    jsLibs: [
        '/website/static/lib/YTPlayer/jquery.mb.YTPlayer.js',
    ],
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        this._startVideo();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._stopVideo();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When user provides video this method will update the video type according 
     * to the input.
     *
     * @private
     */
    _updateVideoType: function () {
        var regexUrl = '((?:https?:)?//([^\\s\'"<>\\\\/]+)/([^\\s\'"<>\\\\]+))';
        var match = this.src.match(new RegExp('\\ssrc=[\'"]?' + regexUrl));
        match = match || this.src.match(new RegExp('^\\s*' + regexUrl));
        if (!match) {
            this.videoType = "image";
            this.src = "";
            return;
        }

        var url = match[1];
        var domain = match[2];
        var path = match[3];

        match = undefined;

        var servicesPrefix = {
            youtube: 'https://youtu.be/',
            vimeo: 'https://vimeo.com/',
            dailymotion: 'http://dai.ly/',
        };

        if (/\.youtube(-nocookie)?\./.test(domain)) {
            this.videoType = 'Youtube';
            match = path.match(/^(?:embed\/|watch\?v=)?([^\/?&#]+)/i);
        } else if (domain === "youtu.be") {
            this.videoType = 'Youtube';
            match = path.match(/^([^\/?&#]+)/);
        } else if (_.str.include(domain, "vimeo.")) {
            this.videoType = 'vimeo';
            match = path.match(/^(?:video\/)?([^?&#]+)/i);
        } else if (_.str.include(domain, ".dailymotion.")) {
            this.videoType = "dailymotion";
            match = path.match(/(?:embed\/)?(?:video\/)?([^\/?&#_]+)/i);
        } else if (domain === "dai.ly") {
            this.videoType = "dailymotion";
            match = path.match(/^([^\/?&#]+)/);
        }

        if (match) {
            this.src = servicesPrefix[this.videoType] + match[1];
        } else if (!/\ssrc=/.test(this.src)) {
            this.src = url;
            this.videoType = 'html5';
        } else {
            this.videoType = 'other';
        }

        this.$target.data('video-type', this.videoType);
    },

    /**
     * When user provides video this method will be called first.
     *
     * @private
     */
    _startVideo: function () {
        var self = this;
        var videoUrl;

        if (!this.videoType || this.src !== this.$target.attr('src')) {
            this.src = this.$target.attr('src');
            if (!this.src) {
                return;
            }
            this._updateVideoType();
        }
        var params = _.chain(['muted', 'loop', 'autoplay', 'controls']).map(function (attribute) {
            var value = self.$target.attr(attribute);
            return [attribute, value ? 1 : value];
        }).object().value();
        videoUrl = this.$target.attr('src');

        var whenPlayerReady = (this['_create' + this.videoType + 'Video'] || this['_createVideo']).call(this, self.$target, videoUrl, params);

        whenPlayerReady.then(function ($player) {
            $player.parentsUntil(self.$target).css({width: '100%', height: 'auto'});
            if ($player.is('iframe')) {
                $player.css({width: '100%', height: '100%'});
                self.ratio = 16 / 9;
                if ($player.width() / $player.height() < self.ratio) {
                    $player.width($player.height() * self.ratio);
                    $player.height($player.height());
                } else {
                    $player.width($player.width());
                    $player.height($player.width() / self.ratio);
                }
            } else {
                $player.css({width: '100%', height: 'auto'});
            }
            $(window).trigger('resize');
        });
    },

    /**
     * When user removes snippet or change the video url, the video will
     * be removed by this method.
     *
     * @private
     */
    _stopVideo: function () {
        this.$target.find('.yt_video_container').remove();
    },

    /**
     * When type of video is not youtube this method will create video
     * for other supported types.
     *
     * @private
     * @param {object} $container
     * @param {string} videoUrl
     * @param {object} params
     */
    _createVideo: function ($container, videoUrl, params) {
        var def = new Promise(function (resolve, reject) {
            var $iframe;
            var opacity = $container.attr('opacity');
            if (videoUrl) {
                $container.children().first().removeClass('o_video_bg');
                if ($container.find('iframe').length) {
                    $container.find('iframe').remove();
                }
                $iframe = $('<iframe/>', {
                    frameborder: "0",
                    class: "playerBox o_iframe_position",
                    allowfullscreen: "",
                    src: 'https:' + videoUrl + '&muted=1&controls=0&title=0&byline=0&portrait=0&badge=0&autopause=0',
                });
            } else {
                $iframe = $('<div/>').html(this.src).find('iframe:first').css({
                    height: "100%", width: "100%", top: 0, position: "absolute",
                });
                if ($iframe.length) {
                    $container.css('max-height', '');
                } else {
                    reject();
                }
            }
            $iframe.fadeTo(0, 0);
            $iframe.on('load', function () {
                resolve($iframe);
            });
            $iframe.fadeTo(0, opacity);
            $container.append($iframe);
        });
        return def;
    },

    /**
     * When type of video is youtube this method will be called.
     *
     * @private
     * @param {object} $container
     * @param {string} videoUrl
     * @param {object} _params
     */
    _createYoutubeVideo: function ($container, videoUrl, _params) {
        $container.find('iframe.o_iframe_position').remove();
        var videoId = this.$target.attr('src').split('/')[4].split('?')[0];
        var params = _.mapObject(_params, function (v) { return !!v; });
        var opacity = this.$target.attr('opacity');

        var timeStamp = Date.now();

        var $videoContainer = $('<div/>', {
            class: 'yt_video_container ',
            id: 's_video_block_' + timeStamp,
        });
        var playerParams = {
            videoURL: videoId, containment: '#s_video_block_' + timeStamp, mute: params['muted'], loop: params['loop'],
            stopMovieOnBlur: false, autoPlay: params['autoplay'], showYTLogo: false, opacity: opacity, showControls: false,
        };
        var $el = $('<div/>', {'class': 'player', 'data-property': JSON.stringify(playerParams)});
        var $loader = $("<span class='yt-loader'><span/></span>");
        $videoContainer.append($el).append($loader);

        var interval = null;
        if ($("#oe_main_menu_navbar").length > 0) {
            $loader.css("top", $("#oe_main_menu_navbar").outerHeight()+1);
        }
        $loader.animate({width: "45%"}, 800, function () {
            var el = $loader;
            interval = setInterval(function () { timer(); }, 300);
            function timer() { var w =  el.width(); el.width(w + 5); }
        });

        if (!params['autoplay']) {
            $el.one('YTPStart', function () {
                $el.YTPPause();
            });
        }

        var def = new Promise(function (resolve, reject) {
            $el.on('YTPReady', function () {
                clearInterval(interval);
                $loader.css("width", "100%").fadeOut(500);

                resolve($videoContainer.find('iframe'));

                if (!params['controls'] && params['autoplay']) {
                    return;
                }

                var $controls = $("<span/>", {'class': 'controls'}).appendTo($videoContainer);

                var $btnplay = $("<span/>", {'class': 'fa fa-fw'}).appendTo($controls);
                var playing = params['autoplay'];
                $btnplay.toggleClass("fa-pause", playing).toggleClass("fa-play", !playing);
                $btnplay.on("click", playCallback);
                if (!params['controls']) {
                    $btnplay.one('click', function () {
                        $controls.remove();
                    });
                }

                if (!params['muted'] && params['controls']) {
                    var $btnMute = $("<span/>", {'class': 'fa fa-fw fa-volume-up'}).appendTo($controls);
                    $btnMute.on("click", muteCallback);
                }

                function playCallback() {
                    if (playing) {
                        $el.YTPPause();
                    } else {
                        $el.YTPPlay();
                    }
                    playing = !playing;

                    $btnplay.toggleClass("fa-pause", playing).toggleClass("fa-play", !playing);
                }
                function muteCallback() {
                    $el.YTPToggleVolume();
                    $btnMute.toggleClass("fa-volume-up").toggleClass("fa-volume-off");
                }
            });

            $container.append($videoContainer);
            $el.YTPlayer();
        });
        return def;
    },
}),

registry.parallax = Animation.extend({
    selector: '.parallax',
    effects: [{
        startEvents: 'scroll',
        update: '_onWindowScroll',
    }],

    /**
     * @override
     */
    start: function () {
        this._rebuild();
        $(window).on('resize.animation_parallax', _.debounce(this._rebuild.bind(this), 500));
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(window).off('.animation_parallax');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prepares the background element which will scroll at a different speed
     * according to the viewport dimensions and other snippet parameters.
     *
     * @private
     */
    _rebuild: function () {
        // Add/find bg DOM element to hold the parallax bg (support old v10.0 parallax)
        if (!this.$bg || !this.$bg.length) {
            this.$bg = this.$('> .s_parallax_bg');
            if (!this.$bg.length) {
                this.$bg = $('<span/>', {
                    class: 's_parallax_bg' + (this.$target.hasClass('oe_custom_bg') ? ' oe_custom_bg' : ''),
                }).prependTo(this.$target);
            }
        }
        var urlTarget = this.$target.css('background-image');
        if (urlTarget !== 'none') {
            this.$bg.css('background-image', urlTarget);
        }
        this.$target.css('background-image', 'none');

        // Get parallax speed
        this.speed = parseFloat(this.$target.attr('data-scroll-background-ratio') || 0);

        // Reset offset if parallax effect will not be performed and leave
        this.$target.toggleClass('s_parallax_is_fixed', this.speed === 1);
        if (this.speed === 0 || this.speed === 1) {
            this.$bg.css({
                transform: '',
                top: '',
                bottom: ''
            });
            return;
        }

        // Initialize parallax data according to snippet and viewport dimensions
        this.viewport = document.body.clientHeight - $('#wrapwrap').position().top;
        this.visibleArea = [this.$target.offset().top];
        this.visibleArea.push(this.visibleArea[0] + this.$target.innerHeight() + this.viewport);
        this.ratio = this.speed * (this.viewport / 10);

        // Provide a "safe-area" to limit parallax
        this.$bg.css({
            top: -this.ratio,
            bottom: -this.ratio,
        });
    },

    //--------------------------------------------------------------------------
    // Effects
    //--------------------------------------------------------------------------

    /**
     * Describes how to update the snippet when the window scrolls.
     *
     * @private
     * @param {integer} scrollOffset
     */
    _onWindowScroll: function (scrollOffset) {
        // Speed == 0 is no effect and speed == 1 is handled by CSS only
        if (this.speed === 0 || this.speed === 1) {
            return;
        }

        // Perform translation if the element is visible only
        var vpEndOffset = scrollOffset + this.viewport;
        if (vpEndOffset >= this.visibleArea[0]
         && vpEndOffset <= this.visibleArea[1]) {
            this.$bg.css('transform', 'translateY(' + _getNormalizedPosition.call(this, vpEndOffset) + 'px)');
        }

        function _getNormalizedPosition(pos) {
            // Normalize scroll in a 1 to 0 range
            var r = (pos - this.visibleArea[1]) / (this.visibleArea[0] - this.visibleArea[1]);
            // Normalize accordingly to current options
            return Math.round(this.ratio * (2 * r - 1));
        }
    },
});

registry.share = publicWidget.Widget.extend({
    selector: '.s_share, .oe_share', // oe_share for compatibility

    /**
     * @override
     */
    start: function () {
        var urlRegex = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/;
        var titleRegex = /(\?(?:|.*&)(?:title|text|subject)=)(.*?)(&|#|$)/;
        var url = encodeURIComponent(window.location.href);
        var title = encodeURIComponent($('title').text());
        this.$('a').each(function () {
            var $a = $(this);
            $a.attr('href', function (i, href) {
                return href.replace(urlRegex, function (match, a, b, c) {
                    return a + url + c;
                }).replace(titleRegex, function (match, a, b, c) {
                    return a + title + c;
                });
            });
            if ($a.attr('target') && $a.attr('target').match(/_blank/i) && !$a.closest('.o_editable').length) {
                $a.on('click', function () {
                    window.open(this.href, '', 'menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
                    return false;
                });
            }
        });

        return this._super.apply(this, arguments);
    },
});

registry.mediaVideo = publicWidget.Widget.extend({
    selector: '.media_iframe_video',

    /**
     * @override
     */
    start: function () {
        // TODO: this code should be refactored to make more sense and be better
        // integrated with Odoo (this refactoring should be done in master).

        var def = this._super.apply(this, arguments);
        if (this.$target.children('iframe').length) {
            // There already is an <iframe/>, do nothing
            return def;
        }

        // Bug fix / compatibility: empty the <div/> element as all information
        // to rebuild the iframe should have been saved on the <div/> element
        this.$target.empty();

        // Add extra content for size / edition
        this.$target.append(
            '<div class="css_editable_mode_display">&nbsp;</div>' +
            '<div class="media_iframe_video_size">&nbsp;</div>'
        );

        // Rebuild the iframe. Depending on version / compatibility / instance,
        // the src is saved in the 'data-src' attribute or the
        // 'data-oe-expression' one (the latter is used as a workaround in 10.0
        // system but should obviously be reviewed in master).
        this.$target.append($('<iframe/>', {
            src: _.escape(this.$target.data('oe-expression') || this.$target.data('src')),
            frameborder: '0',
            allowfullscreen: 'allowfullscreen',
            sandbox: 'allow-scripts allow-same-origin', // https://www.html5rocks.com/en/tutorials/security/sandboxed-iframes/
        }));

        return def;
    },
});

registry.ul = publicWidget.Widget.extend({
    selector: 'ul.o_ul_folded, ol.o_ul_folded',
    events: {
        'click .o_ul_toggle_next': '_onToggleNextClick',
        'click .o_ul_toggle_self': '_onToggleSelfClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a "toggle next" ul is clicked.
     *
     * @private
     */
    _onToggleNextClick: function (ev) {
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        $target.toggleClass('o_open');
        $target.closest('li').next().toggleClass('o_close');
    },
    /**
     * Called when a "toggle self" ul is clicked.
     *
     * @private
     */
    _onToggleSelfClick: function (ev) {
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        $target.toggleClass('o_open');
        $target.closest('li').find('ul,ol').toggleClass('o_close');
    },
});

registry.gallery = publicWidget.Widget.extend({
    selector: '.o_gallery:not(.o_slideshow)',
    xmlDependencies: ['/website/static/src/xml/website.gallery.xml'],
    events: {
        'click img': '_onClickImg',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when an image is clicked. Opens a dialog to browse all the images
     * with a bigger size.
     *
     * @private
     * @param {Event} ev
     */
    _onClickImg: function (ev) {
        var self = this;
        var $cur = $(ev.currentTarget);

        var urls = [];
        var idx = undefined;
        var milliseconds = undefined;
        var params = undefined;
        var $images = $cur.closest('.o_gallery').find('img');
        var size = 0.8;
        var dimensions = {
            min_width: Math.round(window.innerWidth * size * 0.9),
            min_height: Math.round(window.innerHeight * size),
            max_width: Math.round(window.innerWidth * size * 0.9),
            max_height: Math.round(window.innerHeight * size),
            width: Math.round(window.innerWidth * size * 0.9),
            height: Math.round(window.innerHeight * size)
        };

        $images.each(function () {
            urls.push($(this).attr('src'));
        });
        var $img = ($cur.is('img') === true) ? $cur : $cur.closest('img');
        idx = urls.indexOf($img.attr('src'));

        milliseconds = $cur.closest('.o_gallery').data('interval') || false;
        var $modal = $(qweb.render('website.gallery.slideshow.lightbox', {
            srcs: urls,
            index: idx,
            dim: dimensions,
            interval: milliseconds,
            id: _.uniqueId('slideshow_'),
        }));
        $modal.modal({
            keyboard: true,
            backdrop: true,
        });
        $modal.on('hidden.bs.modal', function () {
            $(this).hide();
            $(this).siblings().filter('.modal-backdrop').remove(); // bootstrap leaves a modal-backdrop
            $(this).remove();
        });
        $modal.find('.modal-content, .modal-body.o_slideshow').css('height', '100%');
        $modal.appendTo(document.body);

        $modal.one('shown.bs.modal', function () {
            self.trigger_up('widgets_start_request', {
                editableMode: false,
                $target: $modal.find('.modal-body.o_slideshow'),
            });
        });
    },
});

registry.gallerySlider = publicWidget.Widget.extend({
    selector: '.o_slideshow',
    xmlDependencies: ['/website/static/src/xml/website.gallery.xml'],
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$carousel = this.$target.is('.carousel') ? this.$target : this.$target.find('.carousel');
        this.$indicator = this.$carousel.find('.carousel-indicators');
        this.$prev = this.$indicator.find('li.o_indicators_left').css('visibility', ''); // force visibility as some databases have it hidden
        this.$next = this.$indicator.find('li.o_indicators_right').css('visibility', '');
        var $lis = this.$indicator.find('li[data-slide-to]');
        var nbPerPage = Math.floor(this.$indicator.width() / $lis.first().outerWidth(true)) - 3; // - navigator - 1 to leave some space
        var realNbPerPage = nbPerPage || 1;
        var nbPages = Math.ceil($lis.length / realNbPerPage);

        var index;
        var page;
        update();

        function hide() {
            $lis.each(function (i) {
                $(this).toggleClass('d-none', i < page * nbPerPage || i >= (page + 1) * nbPerPage);
            });
            if (self.editableMode) { // do not remove DOM in edit mode
                return;
            }
            if (page <= 0) {
                self.$prev.detach();
            } else {
                self.$prev.prependTo(self.$indicator);
            }
            if (page >= nbPages - 1) {
                self.$next.detach();
            } else {
                self.$next.appendTo(self.$indicator);
            }
        }

        function update() {
            index = $lis.index($lis.filter('.active')) || 0;
            page = Math.floor(index / realNbPerPage);
            hide();
        }

        this.$carousel.on('slide.bs.carousel.gallery_slider', function () {
            setTimeout(function () {
                var $item = self.$carousel.find('.carousel-inner .carousel-item-prev, .carousel-inner .carousel-item-next');
                var index = $item.index();
                $lis.removeClass('active')
                    .filter('[data-slide-to="' + index + '"]')
                    .addClass('active');
            }, 0);
        });
        this.$indicator.on('click.gallery_slider', '> li:not([data-slide-to])', function () {
            page += ($(this).hasClass('o_indicators_left') ? -1 : 1);
            page = Math.max(0, Math.min(nbPages - 1, page)); // should not be necessary
            self.$carousel.carousel(page * realNbPerPage);
            hide();
        });
        this.$carousel.on('slid.bs.carousel.gallery_slider', update);

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);

        this.$prev.prependTo(this.$indicator);
        this.$next.appendTo(this.$indicator);
        this.$carousel.off('.gallery_slider');
        this.$indicator.off('.gallery_slider');
    },
});

registry.socialShare = publicWidget.Widget.extend({
    selector: '.oe_social_share',
    xmlDependencies: ['/website/static/src/xml/website.share.xml'],
    events: {
        'mouseenter': '_onMouseEnter',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _bindSocialEvent: function () {
        this.$('.oe_social_facebook').click($.proxy(this._renderSocial, this, 'facebook'));
        this.$('.oe_social_twitter').click($.proxy(this._renderSocial, this, 'twitter'));
        this.$('.oe_social_linkedin').click($.proxy(this._renderSocial, this, 'linkedin'));
        this.$('.oe_social_google-plus').click($.proxy(this._renderSocial, this, 'google-plus'));
    },
    /**
     * @private
     */
    _render: function () {
        this.$el.popover({
            content: qweb.render('website.social_hover', {medias: this.socialList}),
            placement: 'bottom',
            container: this.$el,
            html: true,
            trigger: 'manual',
            animation: false,
        }).popover("show");

        this.$el.off('mouseleave.socialShare').on('mouseleave.socialShare', function () {
            var self = this;
            setTimeout(function () {
                if (!$(".popover:hover").length) {
                    $(self).popover('dispose');
                }
            }, 200);
        });
    },
    /**
     * @private
     */
    _renderSocial: function (social) {
        var url = this.$el.data('urlshare') || document.URL.split(/[?#]/)[0];
        url = encodeURIComponent(url);
        var title = document.title.split(" | ")[0];  // get the page title without the company name
        var hashtags = ' #' + document.title.split(" | ")[1].replace(' ', '') + ' ' + this.hashtags;  // company name without spaces (for hashtag)
        var socialNetworks = {
            'facebook': 'https://www.facebook.com/sharer/sharer.php?u=' + url,
            'twitter': 'https://twitter.com/intent/tweet?original_referer=' + url + '&text=' + encodeURIComponent(title + hashtags + ' - ') + url,
            'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + url + '&title=' + encodeURIComponent(title),
            'google-plus': 'https://plus.google.com/share?url=' + url,
        };
        if (!_.contains(_.keys(socialNetworks), social)) {
            return;
        }
        var wHeight = 500;
        var wWidth = 500;
        window.open(socialNetworks[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + wHeight + ',width=' + wWidth);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the user hovers the animation element -> open the social
     * links popover.
     *
     * @private
     */
    _onMouseEnter: function () {
        var social = this.$el.data('social');
        this.socialList = social ? social.split(',') : ['facebook', 'twitter', 'linkedin', 'google-plus'];
        this.hashtags = this.$el.data('hashtags') || '';

        this._render();
        this._bindSocialEvent();
    },
});

registry.facebookPage = publicWidget.Widget.extend({
    selector: '.o_facebook_page',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        var params = _.pick(this.$el.data(), 'href', 'height', 'tabs', 'small_header', 'hide_cover', 'show_facepile');
        if (!params.href) {
            return def;
        }
        params.width = utils.confine(Math.floor(this.$el.width()), 180, 500);

        var src = $.param.querystring('https://www.facebook.com/plugins/page.php', params);
        this.$iframe = $('<iframe/>', {
            src: src,
            width: params.width,
            height: params.height,
            css: {
                border: 'none',
                overflow: 'hidden',
            },
            scrolling: 'no',
            frameborder: '0',
            allowTransparency: 'true',
        });
        this.$el.append(this.$iframe);

        return def;
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);

        if (this.$iframe) {
            this.$iframe.remove();
        }
    },
});

registry.anchorSlide = publicWidget.Widget.extend({
    selector: 'a[href^="/"][href*="#"], a[href^="#"]',
    events: {
        'click': '_onAnimateClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAnimateClick: function (ev) {
        if (this.$target[0].pathname !== window.location.pathname) {
            return;
        }
        var hash = this.$target[0].hash;
        if (!/^#[\w-]+$/.test(hash)) {
            return;
        }
        var $anchor = $(hash);
        if (!$anchor.length || !$anchor.attr('data-anchor')) {
            return;
        }
        ev.preventDefault();
        $('html, body').animate({
            scrollTop: $anchor.offset().top,
        }, 500);
    },
});

return {
    Widget: publicWidget.Widget,
    Animation: Animation,
    registry: registry,

    Class: Animation, // Deprecated
};
});
