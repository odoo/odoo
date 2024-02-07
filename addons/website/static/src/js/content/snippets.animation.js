odoo.define('website.content.snippets.animation', function (require) {
'use strict';

/**
 * Provides a way to start JS code for snippets' initialization and animations.
 */

const { loadJS } = require('@web/core/assets');
var Class = require('web.Class');
var config = require('web.config');
var core = require('web.core');
const dom = require('web.dom');
var mixins = require('web.mixins');
var publicWidget = require('web.public.widget');
const wUtils = require('website.utils');

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
     * @param {boolean} [options.enableInModal]
     *        when it is true, it means that the 'scroll' event must be
     *        triggered when scrolling a modal.
     */
    init: function (parent, updateCallback, startEvents, $startTarget, options) {
        mixins.ParentedMixin.init.call(this);
        this.setParent(parent);

        options = options || {};
        this._minFrameTime = 1000 / (options.maxFPS || 100);

        // Initialize the animation startEvents, startTarget, endEvents, endTarget and callbacks
        this._updateCallback = updateCallback;
        this.startEvents = startEvents || 'scroll';
        const modalEl = options.enableInModal ? parent.target.closest('.modal') : null;
        const mainScrollingElement = modalEl ? modalEl : $().getScrollingElement()[0];
        const mainScrollingTarget = mainScrollingElement === document.documentElement ? window : mainScrollingElement;
        this.$startTarget = $($startTarget ? $startTarget : this.startEvents === 'scroll' ? mainScrollingTarget : window);
        if (options.getStateCallback) {
            this._getStateCallback = options.getStateCallback;
        } else if (this.startEvents === 'scroll' && this.$startTarget[0] === mainScrollingTarget) {
            const $scrollable = this.$startTarget;
            this._getStateCallback = function () {
                return $scrollable.scrollTop();
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
                enableInModal: desc.enableInModal || undefined,
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
        $(window).on('resize.slider', _.debounce(() => this._computeHeights(), 250));
        if (this.editableMode) {
            // Prevent carousel slide to be an history step.
            this.$target.on('slide.bs.carousel.slider', () => {
                this.options.wysiwyg.odooEditor.observerUnactive();
            });
            this.$target.on('slid.bs.carousel.slider', () => {
                this.options.wysiwyg.odooEditor.observerActive();
            });
        }
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
        $(window).off('.slider');
        this.$target.off('.slider');
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
        _.each($items, el => {
            var $item = $(el);
            var isActive = $item.hasClass('active');
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive('_computeHeights');
            $item.addClass('active');
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive('_computeHeights');
            var height = $item.outerHeight();
            if (height > maxHeight) {
                maxHeight = height;
            }
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive('_computeHeights');
            $item.toggleClass('active', isActive);
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive('_computeHeights');
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

registry.Parallax = Animation.extend({
    selector: '.parallax',
    disabledInEditableMode: false,
    effects: [{
        startEvents: 'scroll',
        update: '_onWindowScroll',
        enableInModal: true,
    }],

    /**
     * @override
     */
    start: function () {
        this._rebuild();
        $(window).on('resize.animation_parallax', _.debounce(this._rebuild.bind(this), 500));
        this.modalEl = this.$target[0].closest('.modal');
        if (this.modalEl) {
            $(this.modalEl).on('shown.bs.modal.animation_parallax', () => {
                this._rebuild();
                this.modalEl.dispatchEvent(new Event('scroll'));
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this._updateBgCss({
            transform: '',
            top: '',
            bottom: '',
        });

        $(window).off('.animation_parallax');
        if (this.modalEl) {
            $(this.modalEl).off('.animation_parallax');
        }
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
        this.$bg = this.$('> .s_parallax_bg');

        // Get parallax speed
        this.speed = parseFloat(this.$target.attr('data-scroll-background-ratio') || 0);

        // Reset offset if parallax effect will not be performed and leave
        var noParallaxSpeed = (this.speed === 0 || this.speed === 1);
        if (noParallaxSpeed) {
            // TODO remove in master, kept for compatibility in stable
            this._updateBgCss({
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
        const absoluteRatio = Math.abs(this.ratio);
        this._updateBgCss({
            top: -absoluteRatio,
            bottom: -absoluteRatio,
        });
    },
    /**
     * Updates the parallax background element style with the provided CSS
     * values.
     * If the editor is enabled, it deactivates the observer during the CSS
     * update.
     *
     * @param {Object} cssValues - The CSS values to apply to the background.
     */
    _updateBgCss(cssValues) {
        if (!this.$bg) {
            // Safety net in case the `destroy` is called before the `start` is
            // executed.
            return;
        }
        if (this.options.wysiwyg) {
            this.options.wysiwyg.odooEditor.observerUnactive('_updateBgCss');
        }
        this.$bg.css(cssValues);
        if (this.options.wysiwyg) {
            this.options.wysiwyg.odooEditor.observerActive('_updateBgCss');
        }
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
            this._updateBgCss({'transform': 'translateY(' + _getNormalizedPosition.call(this, vpEndOffset) + 'px)'});
        }

        function _getNormalizedPosition(pos) {
            // Normalize scroll in a 1 to 0 range
            var r = (pos - this.visibleArea[1]) / (this.visibleArea[0] - this.visibleArea[1]);
            // Normalize accordingly to current options
            return Math.round(this.ratio * (2 * r - 1));
        }
    },
});

const MobileYoutubeAutoplayMixin = {
    /**
     * Takes care of any necessary setup for autoplaying video. In practice,
     * this method will load the youtube iframe API for mobile environments
     * because mobile environments don't support the youtube autoplay param
     * passed in the url.
     *
     * @private
     * @param {string} src - The source url of the video
     */
    _setupAutoplay: function (src) {
        let promise = Promise.resolve();

        this.isYoutubeVideo = src.indexOf('youtube') >= 0;
        this.isMobileEnv = config.device.size_class <= config.device.SIZES.LG && config.device.touch;

        if (this.isYoutubeVideo && this.isMobileEnv && !window.YT) {
            const oldOnYoutubeIframeAPIReady = window.onYouTubeIframeAPIReady;
            promise = new Promise(resolve => {
                window.onYouTubeIframeAPIReady = () => {
                    if (oldOnYoutubeIframeAPIReady) {
                        oldOnYoutubeIframeAPIReady();
                    }
                    return resolve();
                };
            });
            loadJS('https://www.youtube.com/iframe_api');
        }

        return promise;
    },
    /**
     * @private
     * @param {DOMElement} iframeEl - the iframe containing the video player
     */
    _triggerAutoplay: function (iframeEl) {
        // YouTube does not allow to auto-play video in mobile devices, so we
        // have to play the video manually.
        if (this.isMobileEnv && this.isYoutubeVideo) {
            new window.YT.Player(iframeEl, {
                events: {
                    onReady: ev => ev.target.playVideo(),
                }
            });
        }
    },
};

registry.mediaVideo = publicWidget.Widget.extend(MobileYoutubeAutoplayMixin, {
    selector: '.media_iframe_video',

    /**
     * @override
     */
    start: function () {
        // TODO: this code should be refactored to make more sense and be better
        // integrated with Odoo (this refactoring should be done in master).

        const proms = [this._super.apply(this, arguments)];
        let iframeEl = this.$target[0].querySelector(':scope > iframe');

        // The following code is only there to ensure compatibility with
        // videos added before bug fixes or new Odoo versions where the
        // <iframe/> element is properly saved.
        if (!iframeEl) {
            iframeEl = this._generateIframe();
        }

        // We don't want to cause an error that would prevent entering edit mode
        // if there is an iframe that doesn't have a src (this was possible for
        // a while with the media dialog).
        if (!iframeEl || !iframeEl.getAttribute('src')) {
            // Something went wrong: no iframe is present in the DOM and the
            // widget was unable to create one on the fly.
            return Promise.all(proms);
        }

        proms.push(this._setupAutoplay(iframeEl.getAttribute('src')));
        return Promise.all(proms).then(() => {
            this._triggerAutoplay(iframeEl);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _generateIframe: function () {
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
        var src = _.escape(this.$target.data('oe-expression') || this.$target.data('src'));
        // Validate the src to only accept supported domains we can trust
        var m = src.match(/^(?:https?:)?\/\/([^/?#]+)/);
        if (!m) {
            // Unsupported protocol or wrong URL format, don't inject iframe
            return;
        }
        var domain = m[1].replace(/^www\./, '');
        var supportedDomains = ['youtu.be', 'youtube.com', 'youtube-nocookie.com', 'instagram.com', 'vine.co', 'player.vimeo.com', 'vimeo.com', 'dailymotion.com', 'player.youku.com', 'youku.com'];
        if (!_.contains(supportedDomains, domain)) {
            // Unsupported domain, don't inject iframe
            return;
        }
        const iframeEl = $('<iframe/>', {
            src: src,
            frameborder: '0',
            allowfullscreen: 'allowfullscreen',
        })[0];
        this.$target.append(iframeEl);
        return iframeEl;
    },
});

registry.backgroundVideo = publicWidget.Widget.extend(MobileYoutubeAutoplayMixin, {
    selector: '.o_background_video',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var proms = [this._super(...arguments)];

        this.videoSrc = this.el.dataset.bgVideoSrc;
        this.iframeID = _.uniqueId('o_bg_video_iframe_');
        proms.push(this._setupAutoplay(this.videoSrc));
        if (this.isYoutubeVideo && this.isMobileEnv && !this.videoSrc.includes('enablejsapi=1')) {
            // Compatibility: when choosing an autoplay youtube video via the
            // media manager, the API was not automatically enabled before but
            // only enabled here in the case of background videos.
            // TODO migrate those old cases so this code can be removed?
            this.videoSrc += '&enablejsapi=1';
        }

        var throttledUpdate = _.throttle(() => this._adjustIframe(), 50);

        var $dropdownMenu = this.$el.closest('.dropdown-menu');
        if ($dropdownMenu.length) {
            this.$dropdownParent = $dropdownMenu.parent();
            this.$dropdownParent.on('shown.bs.dropdown.backgroundVideo', throttledUpdate);
        }

        $(window).on('resize.' + this.iframeID, throttledUpdate);

        const $modal = this.$target.closest('.modal');
        if ($modal.length) {
            $modal.on('show.bs.modal', () => {
                const videoContainerEl = this.$target[0].querySelector('.o_bg_video_container');
                videoContainerEl.classList.add('d-none');
            });
            $modal.on('shown.bs.modal', () => {
                this._adjustIframe();
                const videoContainerEl = this.$target[0].querySelector('.o_bg_video_container');
                videoContainerEl.classList.remove('d-none');
            });
        }
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
        this._triggerAutoplay(this.$iframe[0]);
    },
});

registry.socialShare = publicWidget.Widget.extend({
    selector: '.oe_social_share',
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
            'linkedin': 'https://www.linkedin.com/sharing/share-offsite/?url=' + url,
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
     * @returns {Promise}
     */
    async _scrollTo($el, scrollValue = 'true') {
        return dom.scrollTo($el[0], {
            duration: scrollValue === 'true' ? 500 : 0,
            extraOffset: this._computeExtraOffset(),
        });
    },
    /**
     * @private
     */
    _computeExtraOffset() {
        return 0;
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
        if (hash === '#top' || hash === '#bottom') {
            // If the anchor targets #top or #bottom, directly call the
            // "scrollTo" function. The reason is that the header or the footer
            // could have been removed from the DOM. By receiving a string as
            // parameter, the "scrollTo" function handles the scroll to the top
            // or to the bottom of the document even if the header or the
            // footer is removed from the DOM.
            dom.scrollTo(hash, {
                duration: 500,
                extraOffset: this._computeExtraOffset(),
            });
            return;
        }
        if (!hash.length) {
            return;
        }
        // Escape special characters to make the jQuery selector to work.
        hash = '#' + $.escapeSelector(hash.substring(1));
        var $anchor = $(hash);
        const scrollValue = $anchor.attr('data-anchor');
        if (!$anchor.length || !scrollValue) {
            return;
        }

        const collapseMenuEl = this.el.closest('#top_menu_collapse');
        if (collapseMenuEl && collapseMenuEl.classList.contains('show')) {
            // Special case for anchors in collapse: clicking on those scrolls
            // the page but doesn't close the menu. Two issues:
            // 1. There is a visual glitch: the menu is jumping during the
            //    scroll
            // 2. The menu can actually cover the whole screen in mobile if the
            //    menu are long enough. Then it behaves as if the click did
            //    nothing since the page scrolled behind the menu but you didn't
            //    see it and the menu remains open.
            $(collapseMenuEl).collapse("hide");
        }

        ev.preventDefault();
        this._scrollTo($anchor, scrollValue);
    },
});

registry.FullScreenHeight = publicWidget.Widget.extend({
    selector: '.o_full_screen_height',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start() {
        this.inModal = !!this.el.closest('.modal');

        // TODO maybe review the way the public widgets work for non-visible-at-
        // load snippets -> probably better to not do anything for them and
        // start the widgets only once they become visible..?
        if (this.$el.is(':not(:visible)') || this.$el.outerHeight() > this._computeIdealHeight()) {
            // Only initialize if taller than the ideal height as some extra css
            // rules may alter the full-screen-height class behavior in some
            // cases (blog...).
            this._adaptSize();
            $(window).on('resize.FullScreenHeight', _.debounce(() => this._adaptSize(), 250));
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        $(window).off('.FullScreenHeight');
        this.el.style.setProperty('min-height', '');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptSize() {
        const height = this._computeIdealHeight();
        this.el.style.setProperty('min-height', `${height}px`, 'important');
    },
    /**
     * @private
     */
    _computeIdealHeight() {
        const windowHeight = $(window).outerHeight();
        if (this.inModal) {
            return (windowHeight - $('#wrapwrap').position().top);
        }

        // Doing it that way allows to considerer fixed headers, hidden headers,
        // connected users, ...
        const firstContentEl = $('#wrapwrap > main > :first-child')[0]; // first child to consider the padding-top of main
        // When a modal is open, we remove the "modal-open" class from the body.
        // This is because this class sets "#wrapwrap" and "<body>" to
        // "overflow: hidden," preventing the "closestScrollable" function from
        // correctly recognizing the scrollable element closest to the element
        // for which the height needs to be calculated. Without this, the
        // "mainTopPos" variable would be incorrect.
        const modalOpen = document.body.classList.contains("modal-open");
        document.body.classList.remove("modal-open");
        const mainTopPos = firstContentEl.getBoundingClientRect().top + dom.closestScrollable(firstContentEl.parentNode).scrollTop;
        document.body.classList.toggle("modal-open", modalOpen);
        return (windowHeight - mainTopPos);
    },
});

registry.ScrollButton = registry.anchorSlide.extend({
    selector: '.o_scroll_button',

    /**
     * @override
     */
    _onAnimateClick: function (ev) {
        ev.preventDefault();
        // Scroll to the next visible element after the current one.
        const currentSectionEl = this.el.closest('section');
        let nextEl = currentSectionEl.nextElementSibling;
        while (nextEl) {
            if ($(nextEl).is(':visible')) {
                this._scrollTo($(nextEl));
                return;
            }
            nextEl = nextEl.nextElementSibling;
        }
    },
});

registry.FooterSlideout = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.o_footer_slideout)',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        const $main = this.$('> main');
        const slideoutEffect = $main.outerHeight() >= $(window).outerHeight();
        this.el.classList.toggle('o_footer_effect_enable', slideoutEffect);

        // Add a pixel div over the footer, after in the DOM, so that the
        // height of the footer is understood by Firefox sticky implementation
        // (which it seems to not understand because of the combination of 3
        // items: the footer is the last :visible element in the #wrapwrap, the
        // #wrapwrap uses flex layout and the #wrapwrap is the element with a
        // scrollbar).
        // TODO check if the hack is still needed by future browsers.
        this.__pixelEl = document.createElement('div');
        this.__pixelEl.style.width = `1px`;
        this.__pixelEl.style.height = `1px`;
        this.__pixelEl.style.marginTop = `-1px`;
        // On safari, add a background attachment fixed to fix the glitches that
        // appear when scrolling the page with a footer slide out.
        if (/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) {
            this.__pixelEl.style.backgroundColor = "transparent";
            this.__pixelEl.style.backgroundAttachment = "fixed";
            this.__pixelEl.style.backgroundImage = "url(/website/static/src/img/website_logo.svg)";
        }
        this.el.appendChild(this.__pixelEl);

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.el.classList.remove('o_footer_effect_enable');
        this.__pixelEl.remove();
    },
});

registry.TopMenuCollapse = publicWidget.Widget.extend({
    selector: "header #top_menu_collapse",

    /**
     * @override
     */
    async start() {
        this.throttledResize = _.throttle(() => this._onResize(), 25);
        window.addEventListener("resize", this.throttledResize);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        window.removeEventListener("resize", this.throttledResize);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onResize() {
        if (this.el.classList.contains("show")) {
            const togglerEl = this.el.closest("nav").querySelector(".navbar-toggler");
            if (getComputedStyle(togglerEl).display === "none") {
                this.$el.collapse("hide");
            }
        }
    },
});

registry.HeaderHamburgerFull = publicWidget.Widget.extend({
    selector: 'header:has(.o_header_hamburger_full_toggler):not(:has(.o_offcanvas_menu_toggler))',
    events: {
        'click .o_header_hamburger_full_toggler': '_onToggleClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onToggleClick() {
        document.body.classList.add('overflow-hidden');
        setTimeout(() => $(window).trigger('scroll'), 100);
    },
});

registry.BottomFixedElement = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     */
    async start() {
        this.$scrollingElement = $().getScrollingElement();
        this.__hideBottomFixedElements = _.debounce(() => this._hideBottomFixedElements(), 100);
        this.$scrollingElement.on('scroll.bottom_fixed_element', this.__hideBottomFixedElements);
        $(window).on('resize.bottom_fixed_element', this.__hideBottomFixedElements);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$scrollingElement.off('.bottom_fixed_element');
        $(window).off('.bottom_fixed_element');
        this._restoreBottomFixedElements($('.o_bottom_fixed_element'));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Hides the elements that are fixed at the bottom of the screen if the
     * scroll reaches the bottom of the page and if the elements hide a button.
     *
     * @private
     */
    _hideBottomFixedElements() {
        // Note: check in the whole DOM instead of #wrapwrap as unfortunately
        // some things are still put outside of the #wrapwrap (like the livechat
        // button which is the main reason of this code).
        const $bottomFixedElements = $('.o_bottom_fixed_element');
        if (!$bottomFixedElements.length) {
            return;
        }

        // The bottom fixed elements are always hidden when a modal is open
        // thanks to the CSS that is based on the 'modal-open' class added to
        // the body. However, when the modal does not have a backdrop (e.g.
        // cookies bar), this 'modal-open' class is not added. That's why we
        // handle it here. Note that the popup widget code triggers a 'scroll'
        // event when the modal is hidden to make the bottom fixed elements
        // reappear.
        if (this.el.querySelector('.s_popup_no_backdrop.show')) {
            for (const el of $bottomFixedElements) {
                el.classList.add('o_bottom_fixed_element_hidden');
            }
            return;
        }

        this._restoreBottomFixedElements($bottomFixedElements);
        if ((this.$scrollingElement[0].offsetHeight + this.$scrollingElement[0].scrollTop) >= (this.$scrollingElement[0].scrollHeight - 2)) {
            const buttonEls = [...this.$('a:visible, .btn:visible')];
            for (const el of $bottomFixedElements) {
                const hiddenButtonEl = buttonEls.find(button => dom.areColliding(button, el));
                if (hiddenButtonEl) {
                    if (el.classList.contains('o_bottom_fixed_element_move_up')) {
                        el.style.marginBottom = window.innerHeight - hiddenButtonEl.getBoundingClientRect().top + 5 + 'px';
                    } else {
                        el.classList.add('o_bottom_fixed_element_hidden');
                    }
                }
            }
        }
    },
    /**
     * @private
     * @param {jQuery} $elements bottom fixed elements to restore.
     */
    _restoreBottomFixedElements($elements) {
        $elements.removeClass('o_bottom_fixed_element_hidden');
        $elements.filter('.o_bottom_fixed_element_move_up').css('margin-bottom', '');
    },
});

registry.WebsiteAnimate = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    disabledInEditableMode: false,

    offsetRatio: 0.3, // Dynamic offset ratio: 0.3 = (element's height/3)
    offsetMin: 10, // Minimum offset for small elements (in pixels)

    /**
     * @override
     */
    start() {
        this.lastScroll = 0;
        this.$scrollingElement = $().getScrollingElement();
        this.$animatedElements = this.$('.o_animate');

        // Fix for "transform: none" not overriding keyframe transforms on
        // some iPhone using Safari. Note that all animated elements are checked
        // (not only one) as the bug is not systematic and may depend on some
        // other conditions (for example: an animated image in a block which is
        // hidden on mobile would not have the issue).
        const couldOverflowBecauseOfSafariBug = [...this.$animatedElements].some(el => {
            return window.getComputedStyle(el).transform !== 'none';
        });
        this.forceOverflowXYHidden = false;
        if (couldOverflowBecauseOfSafariBug) {
            this._toggleOverflowXYHidden(true);
            // Now prevent any call to _toggleOverflowXYHidden to have an effect
            this.forceOverflowXYHidden = true;
        }

        // By default, elements are hidden by the css of o_animate.
        // Render elements and trigger the animation then pause it in state 0.
        _.each(this.$animatedElements, el => {
            if (el.closest('.dropdown')) {
                el.classList.add('o_animate_in_dropdown');
                return;
            }
            if (!el.classList.contains('o_animate_on_scroll')) {
                this._resetAnimation($(el));
            }
        });
        // Then we render all the elements, the ones which are invisible
        // in state 0 (like fade_in for example) will stay invisible.
        this.$animatedElements.css("visibility", "visible");

        // We use addEventListener instead of jQuery because we need 'capture'.
        // Setting capture to true allows to take advantage of event bubbling
        // for events that otherwise don’t support it. (e.g. useful when
        // scrolling a modal)
        this.__onScrollWebsiteAnimate = _.throttle(this._onScrollWebsiteAnimate.bind(this), 10);
        this.$scrollingElement[0].addEventListener('scroll', this.__onScrollWebsiteAnimate, {capture: true});

        $(window).on('resize.o_animate, shown.bs.modal.o_animate, slid.bs.carousel.o_animate, shown.bs.tab.o_animate, shown.bs.collapse.o_animate', () => {
            this.windowsHeight = $(window).height();
            this._scrollWebsiteAnimate(this.$scrollingElement[0]);
        }).trigger("resize");

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target.find('.o_animate')
            .removeClass('o_animating o_animated o_animate_preview o_animate_in_dropdown')
            .css({
                'animation-name': '',
                'animation-play-state': '',
                'visibility': '',
            });
        $(window).off('.o_animate');
        this.$scrollingElement[0].removeEventListener('scroll', this.__onScrollWebsiteAnimate, {capture: true});
        this.$scrollingElement[0].classList.remove('o_wanim_overflow_xy_hidden');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Starts animation and/or update element's state.
     *
     * @private
     * @param {jQuery} $el
     */
    _startAnimation($el) {
        // Forces the browser to redraw using setTimeout.
        setTimeout(() => {
            this._toggleOverflowXYHidden(true);
            $el
            .css({"animation-play-state": "running"})
            .addClass("o_animating")
            .one('webkitAnimationEnd oanimationend msAnimationEnd animationend', () => {
                $el.addClass("o_animated").removeClass("o_animating");
                this._toggleOverflowXYHidden(false);
                $(window).trigger("resize");
            });
        });
    },
    /**
     * @private
     * @param {jQuery} $el
     */
    _resetAnimation($el) {
        const animationName = $el.css("animation-name");
        $el.css({"animation-name": "dummy-none", "animation-play-state": ""})
           .removeClass("o_animated o_animating");

        this._toggleOverflowXYHidden(false);
        // trigger a DOM reflow
        void $el[0].offsetWidth;
        $el.css({'animation-name': animationName , 'animation-play-state': 'paused'});
    },
    /**
     * Shows/hides the horizontal scrollbar (on the #wrapwrap) and prevents
     * flicker of the page height (on the slideout footer).
     *
     * @private
     * @param {Boolean} add
     */
    _toggleOverflowXYHidden(add) {
        if (this.forceOverflowXYHidden) {
            return;
        }
        if (add) {
            this.$scrollingElement[0].classList.add('o_wanim_overflow_xy_hidden');
        } else if (!this.$scrollingElement.find('.o_animating').length) {
            this.$scrollingElement[0].classList.remove('o_wanim_overflow_xy_hidden');
        }
    },
    /**
     * Gets element top offset by not taking CSS transforms into calculations.
     *
     * @private
     * @param {Element} el
     * @param {HTMLElement} [topEl] if specified, calculates the top distance to
     *     this element.
     */
    _getElementOffsetTop(el, topEl) {
        // Loop through the DOM tree and add its parent's offset to get page offset.
        var top = 0;
        do {
            top += el.offsetTop || 0;
            el = el.offsetParent;
            if (topEl && el === topEl) {
                return top;
            }
        } while (el);
        return top;
    },
    /**
     * @private
     * @param {Element} el
     */
    _scrollWebsiteAnimate(el) {
        _.each(this.$target.find('.o_animate:not(.o_animate_in_dropdown)'), el => {
            const $el = $(el);
            const elHeight = el.offsetHeight;
            const animateOnScroll = el.classList.contains('o_animate_on_scroll');
            let elOffset = animateOnScroll ? 0 : Math.max((elHeight * this.offsetRatio), this.offsetMin);
            const state = $el.css("animation-play-state");

            // We need to offset for the change in position from some animation.
            // So we get the top value by not taking CSS transforms into calculations.
            // Cookies bar might be opened and considered as a modal but it is
            // not really one when there is no backdrop (eg 'discrete' layout),
            // and should not be used as scrollTop value.
            const closestModal = $el.closest(".modal:visible")[0];
            let scrollTop = this.$scrollingElement[0].scrollTop;
            if (closestModal) {
                scrollTop = closestModal.classList.contains("s_popup_no_backdrop") ?
                    closestModal.querySelector(".modal-content").scrollTop :
                    closestModal.scrollTop;
            }
            const elTop = this._getElementOffsetTop(el) - scrollTop;
            let visible;
            const footerEl = el.closest('.o_footer_slideout');
            const wrapEl = this.$target[0];
            if (footerEl && wrapEl.classList.contains('o_footer_effect_enable')) {
                // Since the footer slideout is always in the viewport but not
                // always displayed, the way to calculate if an element is
                // visible in the footer is different. We decided to handle this
                // case specifically instead of a generic solution using
                // elementFromPoint as it is a rare case and the implementation
                // would have been too complicated for such a small use case.
                const actualScroll = wrapEl.scrollTop + this.windowsHeight;
                const totalScrollHeight = wrapEl.scrollHeight;
                const heightFromFooter = this._getElementOffsetTop(el, footerEl);
                visible = actualScroll >=
                    totalScrollHeight - heightFromFooter - elHeight + elOffset;
            } else {
                visible = this.windowsHeight > (elTop + elOffset) &&
                    0 < (elTop + elHeight - elOffset);
            }
            if (animateOnScroll) {
                if (visible) {
                    const start = 100 / (parseFloat(el.dataset.scrollZoneStart) || 1);
                    const end = 100 / (parseFloat(el.dataset.scrollZoneEnd) || 1);
                    const out = el.classList.contains('o_animate_out');
                    const ratio = (out ? elTop + elHeight : elTop) / (this.windowsHeight - (this.windowsHeight / start));
                    const duration = parseFloat(window.getComputedStyle(el).animationDuration);
                    const delay = (ratio - 1) * (duration * end);
                    el.style.animationDelay = (out ? - duration - delay : delay) + "s";
                    el.classList.add('o_animating');
                    this._toggleOverflowXYHidden(true);
                } else if (el.classList.contains('o_animating')) {
                    el.classList.remove('o_animating');
                    this._toggleOverflowXYHidden(false);
                }
            } else {
                if (visible && state === 'paused') {
                    $el.addClass('o_visible');
                    this._startAnimation($el);
                } else if (!visible && $el.hasClass('o_animate_both_scroll') && state === 'running') {
                    $el.removeClass('o_visible');
                    this._resetAnimation($el);
                }
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onScrollWebsiteAnimate(ev) {
        this._scrollWebsiteAnimate(ev.currentTarget);
    },
});

/**
 * The websites, by default, use image lazy loading via the loading="lazy"
 * attribute on <img> elements. However, this does not work great on all
 * browsers. This widget fixes the behaviors with as less code as possible.
 */
registry.ImagesLazyLoading = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     */
    start() {
        // For each image on the page, force a 1px min-height so that Chrome
        // understands the image exists on different zoom sizes of the browser.
        // Indeed, without this, on a 90% zoom, some images were never loaded.
        // Once the image has been loaded, the 1px min-height is removed.
        // Note: another possible solution without JS would be this CSS rule:
        // ```
        // [loading="lazy"] {
        //     min-height: 1px;
        // }
        // ```
        // This would solve the problem the same way with a CSS rule with a
        // very small priority (any class setting a min-height would still have
        // priority). However, the min-height would always be forced even once
        // the image is loaded, which could mess with some layouts relying on
        // the image intrinsic min-height.
        const imgEls = this.$target[0].querySelectorAll('img[loading="lazy"]');
        for (const imgEl of imgEls) {
            // Write initial min-height on the dataset, so that it can also
            // be properly restored on widget destroy.
            imgEl.dataset.lazyLoadingInitialMinHeight = imgEl.style.minHeight;
            imgEl.style.minHeight = '1px';
            wUtils.onceAllImagesLoaded($(imgEl)).then(() => {
                if (this.isDestroyed()) {
                    return;
                }
                this._restoreImage(imgEl);
            });
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        const imgEls = this.$target[0].querySelectorAll('img[data-lazy-loading-initial-min-height]');
        for (const imgEl of imgEls) {
            this._restoreImage(imgEl);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {HTMLImageElement} imgEl
     */
    _restoreImage(imgEl) {
        imgEl.style.minHeight = imgEl.dataset.lazyLoadingInitialMinHeight;
        delete imgEl.dataset.lazyLoadingInitialMinHeight;
    },
});

/**
 * @todo while this solution mitigates the issue, it is not fixing it entirely
 * but mainly, we should find a better solution than a JS solution as soon as
 * one is available and ideally without having to make ugly patches to the SVGs.
 *
 * Due to a bug on Chrome when using browser zoom, there is sometimes a gap
 * between sections with shapes. This gap is due to a rounding issue when
 * positioning the SVG background images. This code reduces the rounding error
 * by ensuring that shape elements always have a width value as close to an
 * integer as possible.
 *
 * Note: a gap also appears between some shapes without zoom. This is likely
 * due to error in the shapes themselves. Many things were done to try and fix
 * this, but the remaining errors will likely be fixed with a review of the
 * shapes in future Odoo versions.
 *
 * /!\
 * If a better solution for stable comes up, this widget behavior may be
 * disabled, avoid depending on it if possible.
 * /!\
 */
registry.ZoomedBackgroundShape = publicWidget.Widget.extend({
    selector: '.o_we_shape',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start() {
        this._onBackgroundShapeResize();
        this.throttledShapeResize = _.throttle(() => this._onBackgroundShapeResize(), 25);
        window.addEventListener('resize', this.throttledShapeResize);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._updateShapePosition();
        window.removeEventListener('resize', this.throttledShapeResize);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the left and right offset of the shape.
     *
     * @private
     * @param {string} offset
     */
    _updateShapePosition(offset = '') {
        this.el.style.left = offset;
        this.el.style.right = offset;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBackgroundShapeResize() {
        this._updateShapePosition();
        // Get the decimal part of the shape element width.
        let decimalPart = this.el.getBoundingClientRect().width % 1;
        // Round to two decimal places.
        decimalPart = Math.round((decimalPart + Number.EPSILON) * 100) / 100;
        // If there is a decimal part. (e.g. Chrome + browser zoom enabled)
        if (decimalPart > 0) {
            // Compensate for the gap by giving an integer width value to the
            // shape by changing its "right" and "left" positions.
            let offset = (decimalPart < 0.5 ? decimalPart : decimalPart - 1) / 2;
            // This never causes the horizontal scrollbar to appear because it
            // only appears if the overflow to the right exceeds 0.333px.
            this._updateShapePosition(offset + 'px');
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
