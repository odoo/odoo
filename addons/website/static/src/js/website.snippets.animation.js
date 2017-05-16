odoo.define('website.snippets.animation', function (require) {
'use strict';

var ajax = require('web.ajax');
var Class = require('web.Class');
var core = require('web.core');
var base = require('web_editor.base');
var animation = require('web_editor.snippets.animation');

var qweb = core.qweb;

// Initialize fallbacks for the use of requestAnimationFrame, cancelAnimationFrame and performance.now()
window.requestAnimationFrame = window.requestAnimationFrame
    || window.webkitRequestAnimationFrame
    || window.mozRequestAnimationFrame
    || window.msRequestAnimationFrame
    || window.oRequestAnimationFrame
    || function (callback) { window.setTimeout(callback, 10); };

window.cancelAnimationFrame = window.cancelAnimationFrame
    || window.webkitCancelAnimationFrame
    || window.mozCancelAnimationFrame
    || window.msCancelAnimationFrame
    || window.oCancelAnimationFrame
    || function (id) { window.clearTimeout(id); };

if (!window.performance || !window.performance.now) window.performance = {now: function () { return Date.now(); }};

/**
 * The AnimationComponent class in in charge of handling one animation loop using the requestAnimationFrame
 * feature. This is used by the Animation class below and should not be called directly by an end developer.
 * The component contains a simple API, it can be started, stopped, played and paused.
 */
var AnimationComponent = Class.extend({
    init: function (parent, updateCallback, startEvents, $startTarget, options) {
        this.parent = parent; // The Animation class instance which is using this component

        options = options || {};
        this._minFrameTime = 1000 / (options.maxFPS || 100);

        // Initialize the animation startEvents, startTarget, endEvents, endTarget and callbacks
        this._updateCallback = updateCallback || function () {};
        this.startEvents = startEvents || "scroll";
        this.$startTarget = $($startTarget || window);
        this._getStateCallback = options.getStateCallback
            || ((this.startEvents === "scroll" && this.$startTarget[0] === window) ? function () { return window.pageYOffset; } : false)
            || ((this.startEvents === "resize" && this.$startTarget[0] === window) ? function () { return {width: window.innerWidth, height: window.innerHeight}; } : false)
            || function () { return undefined; };
        this.endEvents = options.endEvents || false;
        this.$endTarget = options.$endTarget ? $(options.$endTarget) : this.$startTarget;

        // Add a namespace to events using the generated uid
        this._uid = "_animationComponent" + _.uniqueId();
        this.startEvents = _processEvents(this.startEvents, this._uid);
        if (this.endEvents) {
            this.endEvents =  _processEvents(this.endEvents, this._uid);
        }

        function _processEvents(events, namespace) {
            events = events.split(" ");
            return _.each(events, function (e, index) {
                events[index] += ("." + namespace);
            }).join(" ");
        }
    },
    /**
     * The start method initializes when the animation must be played and paused and initializes the
     * animation first frame.
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
             * If there are endEvents, the animation should begin playing when the startEvents are triggered
             * on the startTarget and pause when the endEvents are triggered on the endTarget.
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
             * Else, if there is no endEvent, the animation should begin playing when the startEvents are
             * *continuously* triggered on the startTarget or fully played once. To achieve this, the animation
             * begins playing and is scheduled to pause after 2 seconds. If the startEvents are triggered during
             * that time, the schedule is delayed for another 2 seconds. This allows to describe an "effect"
             * animation (which lasts less than 2 seconds) or an animation which must be playing *during* an event
             * (scroll, mousemove, resize, repeated clicks, ...).
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
     * The stop method pauses the animation and destroys the attached events which trigger the
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
     * The play method forces the requestAnimationFrame loop to start.
     * @param e -> the event which triggered the animation to play
     */
    play: function (e) {
        this._newEvent = e;
        if (!this._paused) return;
        this._paused = false;
        this._rafID = window.requestAnimationFrame(this._update.bind(this));
        this._lastUpdateTimestamp = undefined;
    },
    /**
     * The pause method forces the requestAnimationFrame loop to stop.
     */
    pause: function () {
        if (this._paused) return;
        this._paused = true;
        window.cancelAnimationFrame(this._rafID);
        this._lastUpdateTimestamp = undefined;
    },
    /**
     * The private _update method is the callback which is repeatedly called by the requestAnimationFrame
     * loop. It controls the max fps at which the animation is running and initializes the values that
     * the update callback needs to describe the animation (state, elapsedTime, triggered event).
     * @param timestamp -> the DOMHighResTimeStamp timestamp at which the function is called
     */
    _update: function (timestamp) {
        if (this._paused) return;
        this._rafID = window.requestAnimationFrame(this._update.bind(this));

        // Check the elapsed time since the last update callback call.
        // Consider it 0 if there is no info of last timestamp and leave this _update call if it was
        // called too soon (would overflow the set max FPS).
        var elapsedTime = 0;
        if (this._lastUpdateTimestamp) {
            elapsedTime = timestamp - this._lastUpdateTimestamp;
            if (elapsedTime < this._minFrameTime) return;
        }

        // Check the new animation state thanks to the get state callback and store its new value.
        // If the state is the same as the previous one, leave this _update call, except if there
        // is an event which triggered the "play" method again.
        var animationState = this._getStateCallback.call(this.parent, elapsedTime, this._newEvent);
        if (!this._newEvent && animationState !== undefined && _.isEqual(animationState, this._animationLastState)) return;
        this._animationLastState = animationState;

        // Call the update callback with frame parameters
        this._updateCallback.call(this.parent, this._animationLastState, elapsedTime, this._newEvent);
        this._lastUpdateTimestamp = timestamp; // Save the timestamp at which the update callback was really called
        this._newEvent = undefined; // Forget the event which triggered the last "play" call
    },
});

/**
 * Extend the Animation class to be able to register AnimationComponent's automatically according to
 * the methods it defines. Also allows to register them in more conventional ways by extending the
 * _prepareComponents method and calling the _addComponent method.
 */
animation.Class.include({
    maxFPS: 100, // The max FPS at which all the automatic animation components will be running by default

    /**
     * Extend the start method to prepare animation components and start them.
     */
    start: function () {
        this._super.apply(this, arguments);

        this._prepareComponents();
        _.each(this._animationComponents, function (component) {
            component.start();
        });
    },
    /**
     * Extend the start method to stop animation components and destroy them.
     */
    stop: function () {
        this._super.apply(this, arguments);

        _.each(this._animationComponents, function (component) {
            component.stop();
        });
        this._animationComponents = [];
    },
    /**
     * The private _prepareComponents method is the place to register AnimationComponent instances.
     * This can be done by extending this method and calling the _addComponent method in it or by
     * defining particulary-named methods in the specialized Animation class.
     *
     * The automatic creation of components according to method names is working like this:
     * - Search for methods which match the pattern: on_startEvent[_startTarget[_off_endEvent[_endTarget]]] where:
     *     - startEvent: the event name which triggers the animation to begin playing
     *     - startTarget (optional): the selector (see description below) to find the target where to listen
     *                               for startEvent (if no selector, the window target will be used)
     *     - endEvent (optional): the event name which triggers the end of the animation (if none is defined, the
     *                             animation will stop after a while, @see AnimationComponent.start)
     *     - endTarget (optional): the selector (see description below) to find the target where to listen
     *                             for endEvent (if no selector, the startTarget will be used)
     * - For all of these methods, register the appropriate animation component with the method implementation used
     *   as the update callback. The method receives 3 arguments: the animation state, the elapsedTime since last
     *   update and the event which triggered the animation (undefined if just a new update call without trigger).
     *   The animation state is undefined by default, the scroll offset for the particular "on_scroll" method and
     *   and object with width and height for the particular "on_resize" method. There is the possibility to define
     *   the getState callback of the animation component with this method. For the component created by the definition
     *   of the "on_abc_def", define the "get_state_for_on_abc_def" (so "get_state_for_" followed by the method name).
     *   This allows to improve performance even further in some cases.
     *
     * Selectors mentioned above can be:
     * - the "selector" string: this tells the system to use the Animation instance $target element as target for the
     *   animation component
     * - an underscore-separated list of classnames: for example "leftPanel_playBtn", the system will search inside
     *   the Animation instance $target element for a DOM which matches the selector ".leftPanel .playBtn"
     */
    _prepareComponents: function () {
        this._animationComponents = [];

        var self = this;
        _.each(this.__proto__, function (callback, key) {
            if (!_.isFunction(callback)) return;
            var m = key.match(/^on_([^_]+)(?:_(.+?))?(?:_off_([^_]+)(?:_(.+))?)?$/); // match the pattern described above
            if (!m) return;

            self._addComponent(callback, m[1], _target_from_ugly_selector(m[2]), {
                getStateCallback: self["get_state_for_" + key] || undefined,
                endEvents: m[3] || undefined,
                $endTarget: _target_from_ugly_selector(m[4]),
                maxFPS: self.maxFPS,
            });

            // Return the DOM element matching the selector in the form described above.
            function _target_from_ugly_selector(selector) {
                if (selector) {
                    if (selector === "selector") {
                        return self.$target;
                    } else {
                        return self.$(_.map(selector.split("_"), function (v) {
                            return "." + v;
                        }).join(" "));
                    }
                }
                return undefined;
            }
        });
    },
    /**
     * The private _addComponent method registers a new AnimationComponent according to given parameters
     * @see AnimationComponent.init
     */
    _addComponent: function (updateCallback, startEvents, $startTarget, options) {
        this._animationComponents.push(new AnimationComponent(this, updateCallback, startEvents, $startTarget, options));
    },
});

function load_called_template () {
    var ids_or_xml_ids = _.uniq($("[data-oe-call]").map(function () {return $(this).data('oe-call');}).get());
    if (ids_or_xml_ids.length) {
        ajax.jsonRpc('/website/multi_render', 'call', {
                'ids_or_xml_ids': ids_or_xml_ids
            }).then(function (data) {
                for (var k in data) {
                    var $data = $(data[k]).addClass('o_block_'+k);
                    $("[data-oe-call='"+k+"']").each(function () {
                        $(this).replaceWith($data.clone());
                    });
                }
            });
    }
}

base.ready().then(function () {
    load_called_template();
    if ($(".o_gallery:not(.oe_slideshow)").size()) {
        // load gallery modal template
        ajax.loadXML('/website/static/src/xml/website.gallery.xml', qweb);
    }
});

animation.registry.slider = animation.Class.extend({
    selector: ".carousel",
    start: function () {
        this.$target.carousel();
        return this._super.apply(this, arguments);
    },
    stop: function () {
        this.$target.carousel('pause');
        this.$target.removeData("bs.carousel");
        return this._super.apply(this, arguments);
    },
});

animation.registry.parallax = animation.Class.extend({
    selector: ".parallax",
    start: function () {
        this._super.apply(this, arguments);
        this._rebuild();
        $(window).on("resize.animation_parallax", _.debounce(this._rebuild.bind(this), 500));
    },
    stop: function () {
        this._super.apply(this, arguments);
        $(window).off(".animation_parallax");
    },
    _rebuild: function () {
        // Add/find bg DOM element to hold the parallax bg (support old v10.0 parallax)
        if (!this.$bg || !this.$bg.length) {
            this.$bg = this.$("> .s_parallax_bg");
            if (!this.$bg.length) {
                this.$bg = $("<span/>", {"class": "s_parallax_bg"}).prependTo(this.$target);
            }
        }
        var urlTarget = this.$target.css("background-image");
        if (urlTarget !== "none") {
            this.$bg.css("background-image", urlTarget);
        }
        this.$target.css("background-image", "none");

        // Get parallax speed
        this.speed = parseFloat(this.$target.attr("data-scroll-background-ratio") || 0);

        // Reset offset if parallax effect will not be performed and leave
        this.$target.toggleClass("s_parallax_is_fixed", this.speed === 1);
        if (this.speed === 0 || this.speed === 1) {
            this.$bg.css({
                transform: "",
                top: "",
                bottom: ""
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
            bottom: -this.ratio
        });
    },
    on_scroll: function (scrollOffset) {
        if (this.speed === 0 || this.speed === 1) return;

        // Perform translate if the element is visible only
        var vpEndOffset = scrollOffset + this.viewport;
        if (vpEndOffset >= this.visible_area[0] && vpEndOffset <= this.visible_area[1]) {
            this.$bg.css("transform", "translateY(" + _getNormalizedPosition.call(this, vpEndOffset) + "px)");
        }

        function _getNormalizedPosition(pos) {
            // Normalize scroll in a 1 to 0 range
            var r = (pos - this.visible_area[1]) / (this.visible_area[0] - this.visible_area[1]);
            // Normalize accordingly to current options
            return Math.round(this.ratio * (2 * r - 1));
        }
    }
});

animation.registry.share = animation.Class.extend({
    selector: ".oe_share",
    start: function () {
        var url_regex = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/;
        var title_regex = /(\?(?:|.*&)(?:title|text|subject)=)(.*?)(&|#|$)/;
        var url = encodeURIComponent(window.location.href);
        var title = encodeURIComponent($("title").text());
        this.$("a").each(function () {
            var $a = $(this);
            $a.attr("href", function(i, href) {
                return href.replace(url_regex, function (match, a, b, c) {
                    return a + url + c;
                }).replace(title_regex, function (match, a, b, c) {
                    return a + title + c;
                });
            });
            if ($a.attr("target") && $a.attr("target").match(/_blank/i) && !$a.closest('.o_editable').length) {
                $a.on('click', function () {
                    window.open(this.href,'','menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
                    return false;
                });
            }
        });
        return this._super.apply(this, arguments);
    }
});

animation.registry.media_video = animation.Class.extend({
    selector: ".media_iframe_video",
    start: function () {
        if (!this.$target.has('> iframe').length) {
            var editor = '<div class="css_editable_mode_display">&nbsp;</div>';
            var size = '<div class="media_iframe_video_size">&nbsp;</div>';
            this.$target.html(editor+size+'<iframe src="'+_.escape(this.$target.data("src"))+'" frameborder="0" allowfullscreen="allowfullscreen"></iframe>');
        }
        return this._super.apply(this, arguments);
    },
});

animation.registry.ul = animation.Class.extend({
    selector: "ul.o_ul_folded, ol.o_ul_folded",
    start: function (editable_mode) {
        this.$('.o_ul_toggle_self').off('click').on('click', function (event) {
            $(this).toggleClass('o_open');
            $(this).closest('li').find('ul,ol').toggleClass('o_close');
            event.preventDefault();
        });
        this.$('.o_ul_toggle_next').off('click').on('click', function (event) {
            $(this).toggleClass('o_open');
            $(this).closest('li').next().toggleClass('o_close');
            event.preventDefault();
        });
        return this._super.apply(this, arguments);
    },
});

/**
 * This is a fix for apple device (<= IPhone 4, IPad 2)
 * Standard bootstrap requires data-toggle='collapse' element to be <a/> tags. Unfortunatly one snippet uses a
 * <div/> tag instead. The fix forces an empty click handler on these div, which allows standard bootstrap to work.
 *
 * This should be removed in a future odoo snippets refactoring.
 */
animation.registry._fix_apple_collapse = animation.Class.extend({
    selector: ".s_faq_collapse [data-toggle='collapse']",
    start: function () {
        this.$target.off("click._fix_apple_collapse").on("click._fix_apple_collapse", function () {});
        return this._super.apply(this, arguments);
    },
});

/* -------------------------------------------------------------------------
Gallery Animation

This ads a Modal window containing a slider when an image is clicked
inside a gallery
-------------------------------------------------------------------------*/
animation.registry.gallery = animation.Class.extend({
    selector: ".o_gallery:not(.o_slideshow)",
    start: function () {
        this.$el.on("click", "img", this.click_handler);
        return this._super.apply(this, arguments);
    },
    click_handler : function (event) {
        var $cur = $(event.currentTarget);
        var edition_mode = ($cur.closest("[contenteditable='true']").size() !== 0);

        // show it only if not in edition mode
        if (!edition_mode) {
            var urls = [],
                idx = undefined,
                milliseconds = undefined,
                params = undefined,
                $images = $cur.closest(".o_gallery").find("img"),
                size = 0.8,
                dimensions = {
                    min_width  : Math.round( window.innerWidth  *  size*0.9),
                    min_height : Math.round( window.innerHeight *  size),
                    max_width  : Math.round( window.innerWidth  *  size*0.9),
                    max_height : Math.round( window.innerHeight *  size),
                    width : Math.round( window.innerWidth *  size*0.9),
                    height : Math.round( window.innerHeight *  size)
            };

            $images.each(function () {
                urls.push($(this).attr("src"));
            });
            var $img = ($cur.is("img") === true) ? $cur : $cur.closest("img");
            idx = urls.indexOf($img.attr("src"));

            milliseconds = $cur.closest(".o_gallery").data("interval") || false;
            params = {
                srcs : urls,
                index: idx,
                dim  : dimensions,
                interval : milliseconds,
                id: _.uniqueId("slideshow_")
            };
            var $modal = $(qweb.render('website.gallery.slideshow.lightbox', params));
            $modal.modal({
                keyboard : true,
                backdrop : true
            });
            $modal.on('hidden.bs.modal', function () {
                $(this).hide();
                $(this).siblings().filter(".modal-backdrop").remove(); // bootstrap leaves a modal-backdrop
                $(this).remove();

            });
            $modal.find(".modal-content, .modal-body.o_slideshow").css("height", "100%");
            $modal.appendTo(document.body);

            this.carousel = new animation.registry.gallery_slider($modal.find(".carousel").carousel());
        }
    } // click_handler
});

animation.registry.gallery_slider = animation.Class.extend({
    selector: ".o_slideshow",
    start: function (editable_mode) {
        var self = this;
        this.$carousel = this.$target.is(".carousel") ? this.$target : this.$target.find(".carousel");
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
            if (editable_mode) { // do not remove DOM in edit mode
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
%
        function update() {
            index = $lis.index($lis.filter('.active')) || 0;
            page = Math.floor(index / realNbPerPage);
            hide();
        }

        this.$carousel.on('slide.bs.carousel.gallery_slider', function () {
            setTimeout(function () {
                var $item = self.$carousel.find('.carousel-inner .prev, .carousel-inner .next');
                var index = $item.index();
                $lis.removeClass("active")
                    .filter('[data-slide-to="'+index+'"]')
                    .addClass("active");
            }, 0);
        });
        this.$indicator.on('click.gallery_slider', '> li.fa', function () {
            page += ($(this).hasClass('o_indicators_left') ? -1 : 1);
            page = Math.max(0, Math.min(nbPages - 1, page)); // should not be necessary
            self.$carousel.carousel(page * realNbPerPage);
            hide();
        });
        this.$carousel.on('slid.bs.carousel.gallery_slider', update);
    },
    stop: function () {
        this._super.apply(this, arguments);

        this.$prev.prependTo(this.$indicator);
        this.$next.appendTo(this.$indicator);
        this.$carousel.off('.gallery_slider');
        this.$indicator.off('.gallery_slider');
    },
});

});
