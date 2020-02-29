odoo.define('website.content.snippets.animation', function (require) {
'use strict';

/**
 * Provides a way to start JS code for snippets' initialization and animations.
 */

var Class = require('web.Class');
var config = require('web.config');
var core = require('web.core');
var mixins = require('web.mixins');
var publicWidget = require('web.public.widget');
var utils = require('web.utils');

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
            this.events = _.extend({}, this.events || {}, extraEvents);
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
        'content_changed': '_onContentChanged',
    },

    /**
     * @override
     */
    start: function () {
        this.$('img').on('load.slider', () => this._computeHeights());
        this._computeHeights();
        // Initialize carousel and pause if in edit mode.
        this.$target.carousel(this.editableMode ? 'pause' : undefined);
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
        $items.css('min-height', '');
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
        $items.css('min-height', maxHeight);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onContentChanged: function (ev) {
        this._computeHeights();
    },
});

registry.parallax = Animation.extend({
    selector: '.parallax',
    disabledInEditableMode: false,
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
                    class: 's_parallax_bg',
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
        var noParallaxSpeed = (this.speed === 0 || this.speed === 1);
        this.$target.toggleClass('s_parallax_no_overflow_hidden', noParallaxSpeed);
        if (noParallaxSpeed) {
            this.$bg.css({
                transform: '',
                top: '',
                bottom: '',
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

registry.backgroundVideo = publicWidget.Widget.extend({
    selector: '.o_background_video',
    xmlDependencies: ['/website/static/src/xml/website.background.video.xml'],
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var proms = [this._super(...arguments)];

        this.videoSrc = this.el.dataset.bgVideoSrc;
        this.iframeID = _.uniqueId('o_bg_video_iframe_');

        this.isYoutubeVideo = this.videoSrc.indexOf('youtube') >= 0;
        this.isMobileEnv = config.device.size_class <= config.device.SIZES.LG && config.device.touch;
        if (this.isYoutubeVideo && this.isMobileEnv) {
            this.videoSrc = this.videoSrc + "&enablejsapi=1";

            if (!window.YT) {
                var oldOnYoutubeIframeAPIReady = window.onYouTubeIframeAPIReady;
                proms.push(new Promise(resolve => {
                    window.onYouTubeIframeAPIReady = () => {
                        if (oldOnYoutubeIframeAPIReady) {
                            oldOnYoutubeIframeAPIReady();
                        }
                        return resolve();
                    };
                }));
                $('<script/>', {
                    src: 'https://www.youtube.com/iframe_api',
                }).appendTo('head');
            }
        }

        var throttledUpdate = _.throttle(() => this._adjustIframe(), 50);

        var $dropdownMenu = this.$el.closest('.dropdown-menu');
        if ($dropdownMenu.length) {
            this.$dropdownParent = $dropdownMenu.parent();
            this.$dropdownParent.on('shown.bs.dropdown.backgroundVideo', throttledUpdate);
        }

        $(window).on('resize.' + this.iframeID, throttledUpdate);

        return Promise.all(proms).then(() => this._appendBgVideo());
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);

        if (this.$dropdownParent) {
            this.$dropdownParent.off('.backgroundVideo');
        }

        $(window).off('resize.' + this.iframeID);

        if (this.$bgVideoContainer) {
            this.$bgVideoContainer.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adjusts iframe sizes and position so that it fills the container and so
     * that it is centered in it.
     *
     * @private
     */
    _adjustIframe: function () {
        if (!this.$iframe) {
            return;
        }

        this.$iframe.removeClass('show');

        // Adjust the iframe
        var wrapperWidth = this.$target.innerWidth();
        var wrapperHeight = this.$target.innerHeight();
        var relativeRatio = (wrapperWidth / wrapperHeight) / (16 / 9);
        var style = {};
        if (relativeRatio >= 1.0) {
            style['width'] = '100%';
            style['height'] = (relativeRatio * 100) + '%';
            style['left'] = '0';
            style['top'] = (-(relativeRatio - 1.0) / 2 * 100) + '%';
        } else {
            style['width'] = ((1 / relativeRatio) * 100) + '%';
            style['height'] = '100%';
            style['left'] = (-((1 / relativeRatio) - 1.0) / 2 * 100) + '%';
            style['top'] = '0';
        }
        this.$iframe.css(style);

        void this.$iframe[0].offsetWidth; // Force style addition
        this.$iframe.addClass('show');
    },
    /**
     * Append background video related elements to the target.
     *
     * @private
     */
    _appendBgVideo: function () {
        var $oldContainer = this.$bgVideoContainer || this.$('> .o_bg_video_container');
        this.$bgVideoContainer = $(qweb.render('website.background.video', {
            videoSrc: this.videoSrc,
            iframeID: this.iframeID,
        }));
        this.$iframe = this.$bgVideoContainer.find('.o_bg_video_iframe');
        this.$iframe.one('load', () => {
            this.$bgVideoContainer.find('.o_bg_video_loading').remove();
        });
        this.$bgVideoContainer.prependTo(this.$target);
        $oldContainer.remove();

        this._adjustIframe();

        // YouTube does not allow to auto-play video in mobile devices, so we
        // have to play the video manually.
        if (this.isMobileEnv && this.isYoutubeVideo) {
            new window.YT.Player(this.iframeID, {
                events: {
                    onReady: ev => ev.target.playVideo(),
                }
            });
        }
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
        this.socialList = social ? social.split(',') : ['facebook', 'twitter', 'linkedin'];
        this.hashtags = this.$el.data('hashtags') || '';

        this._render();
        this._bindSocialEvent();
    },
});

registry.anchorSlide = publicWidget.Widget.extend({
    selector: 'a[href^="/"][href*="#"], a[href^="#"]',
    events: {
        'click': '_onAnimateClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQuery} $el the element to scroll to.
     * @param {string} [scrollValue='true'] scroll value
     */
    _scrollTo: function ($el, scrollValue = 'true') {
        const headerHeight = this._computeHeaderHeight();
        $('html, body').animate({
            scrollTop: $el.offset().top - headerHeight,
        }, scrollValue === 'true' ? 500 : 0);
    },
    /**
     * @private
     */
    _computeHeaderHeight: function () {
        let headerHeight = 0;
        const $navbarFixed = $('.o_top_fixed_element');
        _.each($navbarFixed, el => headerHeight += $(el).outerHeight());
        return headerHeight;
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
        if (!utils.isValidAnchor(hash)) {
            return;
        }
        var $anchor = $(hash);
        const scrollValue = $anchor.attr('data-anchor');
        if (!$anchor.length || !scrollValue) {
            return;
        }
        ev.preventDefault();
        this._scrollTo($anchor, scrollValue);
    },
});

registry.ScrollButton = registry.anchorSlide.extend({
    selector: '.o_scroll_button',

    /**
     * @override
     */
    _onAnimateClick: function (ev) {
        ev.preventDefault();
        const $nextSection = this.$el.closest('section').next('section');
        if ($nextSection.length) {
            this._scrollTo($nextSection);
        }
    },
});

return {
    Widget: publicWidget.Widget,
    Animation: Animation,
    registry: registry,

    Class: Animation, // Deprecated
};
});
