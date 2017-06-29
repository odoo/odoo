odoo.define('website.content.snippets.animation', function (require) {
'use strict';

/**
 * Provides a way to start JS code for snippets' initialization and animations.
 */

var Class = require('web.Class');
var core = require('web.core');
var mixins = require('web.mixins');
var Widget = require('web.Widget');

var qweb = core.qweb;

// Initialize fallbacks for the use of requestAnimationFrame,
// cancelAnimationFrame and performance.now()
window.requestAnimationFrame = window.requestAnimationFrame
    || window.webkitRequestAnimationFrame
    || window.mozRequestAnimationFrame
    || window.msRequestAnimationFrame
    || window.oRequestAnimationFrame
    || function (callback) { setTimeout(callback, 10); };
window.cancelAnimationFrame = window.cancelAnimationFrame
    || window.webkitCancelAnimationFrame
    || window.mozCancelAnimationFrame
    || window.msCancelAnimationFrame
    || window.oCancelAnimationFrame
    || function (id) { clearTimeout(id); };
if (!window.performance || !window.performance.now) {
    window.performance = {now: function () { return Date.now(); }};
}

/**
 * In charge of handling one animation loop using the requestAnimationFrame
 * feature. This is used by the `Animation` class below and should not be called
 * directly by an end developer.
 *
 * This uses a simple API: it can be started, stopped, played and paused.
 */
var AnimationComponent = Class.extend(mixins.ParentedMixin, {
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
     *        startEvent is received again)
     * @param {jQuery|DOMElement} [options.$endTarget=$startTarget]
     *        the element(s) on which the endEvent are listened
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
        this._getStateCallback = options.getStateCallback
            || ((this.startEvents === 'scroll' && this.$startTarget[0] === window) ? function () { return window.pageYOffset; } : false)
            || ((this.startEvents === 'resize' && this.$startTarget[0] === window) ? function () { return {width: window.innerWidth, height: window.innerHeight}; } : false)
            || function () { return undefined; };
        this.endEvents = options.endEvents || false;
        this.$endTarget = options.$endTarget ? $(options.$endTarget) : this.$startTarget;

        this._updateCallback = this._updateCallback.bind(parent);
        this._getStateCallback = this._getStateCallback.bind(parent);

        // Add a namespace to events using the generated uid
        this._uid = '_animationComponent' + _.uniqueId();
        this.startEvents = _processEvents(this.startEvents, this._uid);
        if (this.endEvents) {
            this.endEvents =  _processEvents(this.endEvents, this._uid);
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
             * Else, if there is no endEvent, the animation should begin playing
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
        if (!this._paused) return;
        this._paused = false;
        this._rafID = window.requestAnimationFrame(this._update.bind(this));
        this._lastUpdateTimestamp = undefined;
    },
    /**
     * Forces the requestAnimationFrame loop to stop.
     */
    pause: function () {
        if (this._paused) return;
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
        if (this._paused) return;
        this._rafID = window.requestAnimationFrame(this._update.bind(this));

        // Check the elapsed time since the last update callback call.
        // Consider it 0 if there is no info of last timestamp and leave this
        // _update call if it was called too soon (would overflow the set max FPS).
        var elapsedTime = 0;
        if (this._lastUpdateTimestamp) {
            elapsedTime = timestamp - this._lastUpdateTimestamp;
            if (elapsedTime < this._minFrameTime) return;
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
 * Provides a way for executing code once a website DOM element is loaded in the
 * dom and handle the case where the website edit mode is triggered.
 *
 * Also register AnimationComponent automatically according to the methods it
 * defines. Also allows to register them in more conventional ways by extending
 * the `_prepareComponents` method and calling the `_addComponent` method.
 */
var Animation = Widget.extend({
    /**
     * The selector attribute, if defined, allows to automatically create an
     * instance of this animation on page load for each DOM element which
     * matches this selector. The `Animation.$target` element will then be that
     * particular DOM element. This should be the main way of instantiating
     * `Animation` elements.
     */
    selector: false,
    /**
     * Acts as @see Widget.events except that the events are only binded if the
     * Animation instance is instanciated in edit mode.
     */
    edit_events: {},
    /**
     * Acts as @see Widget.events except that the events are only binded if the
     * Animation instance is instanciated in readonly mode.
     */
    read_events: {},
    /**
     * The max FPS at which all the automatic animation components will be
     * running by default.
     */
    maxFPS: 100,

    /**
     * Initializes the events that will need to be binded according to the
     * given mode.
     *
     * @constructor
     * @param {Object} parent
     * @param {boolean} editableMode - true if the page is in edition mode
     */
    init: function (parent, editableMode) {
        this._super.apply(this, arguments);
        this.editableMode = editableMode;
        if (editableMode) {
            this.events = _.extend({}, this.events || {}, this.edit_events || {});
        } else {
            this.events = _.extend({}, this.events || {}, this.read_events || {});
        }
    },
    /**
     * Initializes the animation. The method should not be called directly as
     * called automatically on animation instantiation and on restart.
     *
     * Also, prepares animation components and start them if any.
     *
     * @override
     */
    start: function () {
        this._prepareComponents();
        _.each(this._animationComponents, function (component) {
            component.start();
        });
        return this._super.apply(this, arguments);
    },
    /**
     * Destroys the animation and basically restores the target to the state it
     * was before the start method was called (unlike standard widget, the
     * associated $el DOM is not removed).
     *
     * Also stops animation components and destroys them if any.
     */
    destroy: function () {
        // The difference with the default behavior is that we unset the
        // associated element first so that:
        // 1) its events are unbinded
        // 2) it is not removed from the DOM
        this.setElement(null);
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    setElement: function () {
        this._super.apply(this, arguments);
        this.$target = this.$el;
        this.target = this.el;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Registers `AnimationComponent` instances.
     *
     * This can be done by extending this method and calling the _addComponent
     * method in it or by defining particulary-named methods in the specialized
     * Animation class.
     *
     * The automatic creation of components according to method names is working
     * like this:
     *
     * - Search for methods which match the pattern:
     *   on_startEvent[_startTarget[_off_endEvent[_endTarget]]] where:
     *
     *     - startEvent: the event name which triggers the animation to begin
     *                   playing
     *
     *     - [startTarget]: the selector (see description below) to find the
     *                      target where to listen for startEvent (if no
     *                      selector, the window target will be used)
     *
     *     - [endEvent]: the event name which triggers the end of the animation
     *                   (if none is defined, the animation will stop after a
     *                   while, @see AnimationComponent.start)
     *
     *     - [endTarget]: the selector (see description below) to find the
     *                    target where to listen for endEvent (if no selector,
     *                    the startTarget will be used)
     *
     * - For all of these methods, register the appropriate animation component
     *   with the method implementation used as the update callback. The method
     *   receives 3 arguments: the animation state, the elapsedTime since last
     *   update and the event which triggered the animation (undefined if just a
     *   new update call without trigger).
     *   The animation state is undefined by default, the scroll offset for the
     *   particular "on_scroll" method and and object with width and height for
     *   the particular "on_resize" method. There is the possibility to define
     *   the getState callback of the animation component with this method. For
     *   the component created by the definition of the "on_abc_def", define the
     *   "get_state_for_on_abc_def" (so "get_state_for_" followed by the method
     *   name). This allows to improve performance even further in some cases.
     *
     * Selectors mentioned above can be:
     * - the "selector" string: this tells the system to use the Animation
     *   instance $target element as target for the animation component
     * - an underscore-separated list of classnames: for example with
     *   "leftPanel_playBtn", the system will search inside the Animation
     *   instance $target element for a DOM which matches the selector
     *   ".leftPanel .playBtn"
     *
     * @todo adapt the regex to new conventions and move the functions to a
     *       special key to avoid confusion and bugs
     * @private
     */
    _prepareComponents: function () {
        this._animationComponents = [];

        var self = this;
        _.each(this.__proto__, function (callback, key) {
            if (!_.isFunction(callback)) return;
            // match the pattern described above
            var m = key.match(/^on_([^_]+)(?:_(.+?))?(?:_off_([^_]+)(?:_(.+))?)?$/);
            if (!m) return;

            self._addComponent(callback, m[1], _target_from_ugly_selector(m[2]), {
                getStateCallback: self['get_state_for_' + key] || undefined,
                endEvents: m[3] || undefined,
                $endTarget: _target_from_ugly_selector(m[4]),
                maxFPS: self.maxFPS,
            });

            // Return the DOM element matching the selector in the form
            // described above.
            function _target_from_ugly_selector(selector) {
                if (selector) {
                    if (selector === 'selector') {
                        return self.$target;
                    } else {
                        return self.$(_.map(selector.split('_'), function (v) {
                            return '.' + v;
                        }).join(' '));
                    }
                }
                return undefined;
            }
        });
    },
    /**
     * Registers a new `AnimationComponent` according to given parameters.
     *
     * @private
     * @see AnimationComponent.init
     */
    _addComponent: function (updateCallback, startEvents, $startTarget, options) {
        this._animationComponents.push(
            new AnimationComponent(this, updateCallback, startEvents, $startTarget, options)
        );
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * The registry object contains the list of available animations.
 */
var registry = {};

registry.slider = Animation.extend({
    selector: '.carousel',

    /**
     * @override
     */
    start: function () {
        this.$target.carousel();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.carousel('pause');
        this.$target.removeData('bs.carousel');
    },
});

registry.parallax = Animation.extend({
    selector: '.parallax',

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
        this.visible_area = [this.$target.offset().top];
        this.visible_area.push(this.visible_area[0] + this.$target.innerHeight() + this.viewport);
        this.ratio = this.speed * (this.viewport / 10);

        // Provide a "safe-area" to limit parallax
        this.$bg.css({
            top: -this.ratio,
            bottom: -this.ratio,
        });
    },

    //--------------------------------------------------------------------------
    // Animation Components
    //--------------------------------------------------------------------------

    /**
     * Function which will automatically create an animation component since the
     * shape of its name (@see Animation._prepareComponents). Describes how to
     * update the snippet when the window scrolls.
     *
     * @param {integer} scrollOffset
     */
    on_scroll: function (scrollOffset) {
        // Speed == 0 is no effect and speed == 1 is handled by CSS only
        if (this.speed === 0 || this.speed === 1) {
            return;
        }

        // Perform translation if the element is visible only
        var vpEndOffset = scrollOffset + this.viewport;
        if (vpEndOffset >= this.visible_area[0]
         && vpEndOffset <= this.visible_area[1]) {
            this.$bg.css('transform', 'translateY(' + _getNormalizedPosition.call(this, vpEndOffset) + 'px)');
        }

        function _getNormalizedPosition(pos) {
            // Normalize scroll in a 1 to 0 range
            var r = (pos - this.visible_area[1]) / (this.visible_area[0] - this.visible_area[1]);
            // Normalize accordingly to current options
            return Math.round(this.ratio * (2 * r - 1));
        }
    },
});

registry.share = Animation.extend({
    selector: '.oe_share',

    /**
     * @override
     */
    start: function () {
        var url_regex = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/;
        var title_regex = /(\?(?:|.*&)(?:title|text|subject)=)(.*?)(&|#|$)/;
        var url = encodeURIComponent(window.location.href);
        var title = encodeURIComponent($('title').text());
        this.$('a').each(function () {
            var $a = $(this);
            $a.attr('href', function (i, href) {
                return href.replace(url_regex, function (match, a, b, c) {
                    return a + url + c;
                }).replace(title_regex, function (match, a, b, c) {
                    return a + title + c;
                });
            });
            if ($a.attr('target') && $a.attr('target').match(/_blank/i) && !$a.closest('.o_editable').length) {
                $a.on('click', function () {
                    window.open(this.href,'','menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
                    return false;
                });
            }
        });

        return this._super.apply(this, arguments);
    },
});

registry.mediaVideo = Animation.extend({
    selector: '.media_iframe_video',

    /**
     * @override
     */
    start: function () {
        if (!this.$target.has('> iframe').length) {
            var editor = '<div class="css_editableMode_display">&nbsp;</div>';
            var size = '<div class="media_iframe_video_size">&nbsp;</div>';
            this.$target.html(editor+size);
        }
        this.$target.html(this.$target.html()+'<iframe src="'+_.escape(this.$target.data("src"))+'" frameborder="0" allowfullscreen="allowfullscreen"></iframe>');
        return this._super.apply(this, arguments);
    },
});

registry.ul = Animation.extend({
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

registry.gallery = Animation.extend({
    selector: '.o_gallery:not(.o_slideshow)',
    xmlDependencies: ['/website/static/src/xml/website.gallery.xml'],
    read_events: {
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
        var $cur = $(ev.currentTarget);

        var urls = [];
        var idx = undefined;
        var milliseconds = undefined;
        var params = undefined;
        var $images = $cur.closest('.o_gallery').find('img');
        var size = 0.8;
        var dimensions = {
            min_width  : Math.round( window.innerWidth  *  size*0.9),
            min_height : Math.round( window.innerHeight *  size),
            max_width  : Math.round( window.innerWidth  *  size*0.9),
            max_height : Math.round( window.innerHeight *  size),
            width : Math.round( window.innerWidth *  size*0.9),
            height : Math.round( window.innerHeight *  size)
        };

        $images.each(function () {
            urls.push($(this).attr('src'));
        });
        var $img = ($cur.is('img') === true) ? $cur : $cur.closest('img');
        idx = urls.indexOf($img.attr('src'));

        milliseconds = $cur.closest('.o_gallery').data('interval') || false;
        params = {
            srcs : urls,
            index: idx,
            dim  : dimensions,
            interval : milliseconds,
            id: _.uniqueId('slideshow_')
        };
        var $modal = $(qweb.render('website.gallery.slideshow.lightbox', params));
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

        this.carousel = new registry.gallery_slider($modal.find('.carousel').carousel());
    },
});

registry.gallerySlider = Animation.extend({
    selector: '.o_slideshow',
    xmlDependencies: ['/website/static/src/xml/website.gallery.xml'],

    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$carousel = this.$target.is('.carousel') ? this.$target : this.$target.find('.carousel');
        this.$indicator = this.$carousel.find('.carousel-indicators');
        this.$prev = this.$indicator.find('li.fa:first').css('visibility', ''); // force visibility as some databases have it hidden
        this.$next = this.$indicator.find('li.fa:last').css('visibility', '');
        var $lis = this.$indicator.find('li:not(.fa)');
        var nbPerPage = Math.floor(this.$indicator.width() / $lis.first().outerWidth(true)) - 3; // - navigator - 1 to leave some space
        var realNbPerPage = nbPerPage || 1;
        var nbPages = Math.ceil($lis.length / realNbPerPage);

        var index;
        var page;
        update();

        function hide() {
            $lis.each(function (i) {
                $(this).toggleClass('hidden', !(i >= page*nbPerPage && i < (page+1)*nbPerPage));
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
                var $item = self.$carousel.find('.carousel-inner .prev, .carousel-inner .next');
                var index = $item.index();
                $lis.removeClass('active')
                    .filter('[data-slide-to="'+index+'"]')
                    .addClass('active');
            }, 0);
        });
        this.$indicator.on('click.gallery_slider', '> li.fa', function () {
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

registry.socialShare = Animation.extend({
    selector: '.oe_social_share',
    xmlDependencies: ['/website/static/src/xml/website.share.xml'],
    read_events: {
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
        this.$target.popover({
            content: qweb.render('website.social_hover', {medias: this.socialList}),
            placement: 'bottom',
            container: this.$target,
            html: true,
            trigger: 'manual',
            animation: false,
        }).popover("show");

        this.$target.off('mouseleave.socialShare').on('mouseleave.socialShare', function () {
            var self = this;
            setTimeout(function () {
                if (!$(".popover:hover").length) {
                    $(self).popover("destroy");
                }
            }, 200);
        });
    },
    /**
     * @private
     */
    _renderSocial: function (social) {
        var url = encodeURIComponent(document.URL.split(/[?#]/)[0]);  // get current url without query string
        var title = document.title.split(" | ")[0];  // get the page title without the company name
        var hashtags = ' #'+ document.title.split(" | ")[1].replace(' ','') + ' ' + this.hashtags;  // company name without spaces (for hashtag)
        var social_network = {
            'facebook': 'https://www.facebook.com/sharer/sharer.php?u=' + url,
            'twitter': 'https://twitter.com/intent/tweet?original_referer=' + url + '&text=' + encodeURIComponent(title + hashtags + ' - ' + url),
            'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + url + '&title=' + encodeURIComponent(title),
            'google-plus': 'https://plus.google.com/share?url=' + url,
        };
        if (!_.contains(_.keys(social_network), social)) {
            return;
        }
        var wHeight = 500;
        var wWidth = 500;
        window.open(social_network[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + wHeight + ',width=' + wWidth);
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
        var social = this.$target.data('social');
        this.socialList = social ? social.split(',') : ['facebook', 'twitter', 'linkedin', 'google-plus'];
        this.hashtags = this.$target.data('hashtags') || '';

        this._render();
        this._bindSocialEvent();
    },
});

/**
 * This is a fix for apple device (<= IPhone 4, IPad 2)
 * Standard bootstrap requires data-toggle='collapse' element to be <a/> tags.
 * Unfortunatly one snippet uses a <div/> tag instead. The fix forces an empty
 * click handler on these div, which allows standard bootstrap to work.
 *
 * This should be removed in a future odoo snippets refactoring.
 */
registry._fixAppleCollapse = Animation.extend({
    selector: '.s_faq_collapse [data-toggle="collapse"]',
    events: {
        'click': function () {},
    },
});

return {
    Class: Animation,
    registry: registry,
};
});
