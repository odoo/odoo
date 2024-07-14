/** @odoo-module **/

import { RPCError } from "@web/core/network/rpc_service";
import { renderToElement } from "@web/core/utils/render";
import Widget from "@web/legacy/js/core/widget";
import publicWidget from "@web/legacy/js/public/public_widget";

import { markup } from "@odoo/owl";

var TweetWall = Widget.extend({
    template: 'website_twitter_wall_tweets',

    /**
     * @override
     * @param {number} wall_id
     */
    init: function (parent, wallID) {
        this._super.apply(this, arguments);
        var self = this;
        this.wall_id = wallID;
        this.pool_cache = {};
        this.repeat = false;
        this.shuffle = false;
        this.limit = 25;
        this.num = 1;
        this.timeout = 7000;
        this.last_tweet_id = $('.o-tw-tweet:first').data('tweet-id') || 0;
        this.fetchPromise = undefined;
        this.prependTweetsTo = $('.o-tw-walls-col:first');
        this.interval = setInterval(function () {
            self._getData();
        }, this.timeout);
        var zoomLevel = 1 / (window.devicePixelRatio * 0.80);
        this._zoom(zoomLevel);
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} level
     */
    _zoom: function (level) {
        this.zoomLevel = level;
        document.body.style.transform = `scale(${this.zoomLevel})`;
    },
    /**
     * @private
     */
    _toggleRepeat: function () {
        if (this.repeat) {
            this.repeat = false;
            this.limit = 25;
            Object.values(this.pool_cache).forEach((t) => {
                t.round = t.round ? 1 : 0;
            });
        } else {
            this.repeat = true;
            this.limit = 5;
        }
    },
    /**
     * @private
     */
    _toggleShuffle: function () {
        this.shuffle = this.shuffle === false ? true : false;
    },
    /**
     * @private
     */
    _getData: function () {
        var self = this;
        if (!this.fetchPromise) {
            self.fetchPromise = this.rpc('/twitter_wall/get_tweet/' + self.wall_id, {
                'last_tweet_id': self.last_tweet_id,
            }).then(function (res) {
                self.fetchPromise = undefined;
                if (res.length) {
                    self.last_tweet_id = res[0].id;
                    res.forEach((r) => {
                        r.round = 0;
                        self.pool_cache[r.id] = r;
                    });
                }
                var atLeastOneNotSeen = self.pool_cache.some((t) => t.round === 0);
                if (atLeastOneNotSeen || self.repeat) {
                    self._processTweet();
                }
            }).catch(function (e) {
                self.fetchPromise = undefined;
                if (!(e instanceof RPCError)) {
                    Promise.reject(e);
                }
            });
        }
    },
    /**
     * @private
     */
    _processTweet: function () {
        var self = this;
        var leastRound = Math.min(self.pool_cache.map((o) => o.round)).round;
        // Filter tweets that have not been seen for the most time,
        // excluding the ones that are visible on the screen
        // (the last case is when there is not much tweets to loop on, when looping)
        var tweets = self.pool_cache.filter((f) => {
            var el = $('*[data-tweet-id="' + f.id + '"]');
            if (f.round <= leastRound && (!el.length || el.offset().top > $(window).height())) {
                return f;
            }
        });
        if (this.shuffle) {
            tweets.sort(() => 0.5 - Math.random());
        }
        if (tweets.length) {
            var tweet = tweets[0];
            self.pool_cache[tweet.id].round = leastRound + 1;
            $(renderToElement('website_twitter_wall_tweets', {
                tweet_id: tweet.id,
                tweet: markup(tweet.tweet_html),
            })).prependTo(self.prependTweetsTo);
            var nextPrepend = self.prependTweetsTo.next('.o-tw-walls-col');
            self.prependTweetsTo = nextPrepend.length ? nextPrepend.first() : $('.o-tw-walls-col').first();
        }
    },
    /**
     * @private
     */
    _destroy: function () {
        clearInterval(this.interval);
        this._zoom(1);
    },
});

publicWidget.registry.websiteTwitterWall = publicWidget.Widget.extend({
    selector: '.o-tw-container',
    events: {
        'click .o-tw-tweet-delete': '_onDeleteTweet',
        'click .o-tw-live-btn': '_onLiveButton',
        'click .o-tw-option': '_onOption',
        'click .o-tw-zoom': '_onZoom',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        this.mouseTimer;

        // create an observer instance
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-tweet-id') {
                    $(mutation.target.contentDocument).find('.Tweet-header .Tweet-brand, .Tweet-body .Tweet-actions').remove();
                    $(mutation.target.contentDocument).find('body').css('zoom', $('body').css('zoom'));
                    $(mutation.target.contentDocument).find('.EmbeddedTweet').removeClass('js-clickToOpenTarget');
                }
            });
        });

        // pass in the target node, as well as the observer options
        observer.observe($('.o-tw-walls')[0], {
            attributes: true,
            childList: true,
            characterData: false,
            subtree: true,
        });

        // Initialize widgets
        this.twitterWall = new TweetWall(this, parseInt($('.o-tw-walls').data('wall-id')));

        // Do some stuff on Fullscreen and exit Fullscreen
        $(document).on('webkitfullscreenchange mozfullscreenchange fullscreenchange MSFullscreenChange', function () {
            $('#oe_main_menu_navbar, header, .o-tw-toggle, footer').slideToggle('slow');
            if (document.fullScreen || document.mozFullScreen || document.webkitIsFullScreen) {

                // Hide scroll
                window.scrollTo(0, 0);
                $('body').css({'position': 'fixed'}).addClass('o-tw-view-live');
                $('center.o-tw-tweet > span').hide();
                $('.o-tw-tweet-delete').hide();
                if ($('#oe_main_menu_navbar').length) {
                    $('.o-tw-walls').css('margin-top', '64px');
                } else {
                    $('.o-tw-walls').css('margin-top', '98px');
                }
                // Hide mouse cursor after 2 seconds
                var cursorVisible = true;
                document.onmousemove = function () {
                    if (this.mouseTimer) {
                        window.clearTimeout(this.mouseTimer);
                    }
                    if (!cursorVisible) {
                        document.body.style.cursor = 'default';
                        cursorVisible = true;
                    }
                    this.mouseTimer = window.setTimeout(function () {
                        this.mouseTimer = null;
                        document.body.style.cursor = 'none';
                        cursorVisible = false;
                    }, 2000);
                };
            } else {
                $('body').css({'position': 'initial'}).removeClass('o-tw-view-live');
                $('center.o-tw-tweet > span').show();
                $('.o-tw-tweet-delete').show();
                $('.o-tw-walls').css('margin-top', '0');
                document.body.style.cursor = 'default';
                if (this.mouseTimer) {
                    clearTimeout(this.mouseTimer);
                }
            }
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.twitterWall._destroy();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {number} number
     * @param {string} single
     */
    _setColumns: function (number, single) {
        var cols = $('.o-tw-walls-col').length;
        var i = cols;
        var newCols = [];
        while (i < number) {
            newCols.push($('<div class="o-tw-walls-col col-' + 12 / number + '"></div>').appendTo('.o-tw-walls'));
            i++;
        }
        $('.o-tw-walls-col:gt(' + (number - 1) + ')').remove();
        $('.o-tw-walls-col').removeClass('col-4 col-6 col-12').addClass('col-' + 12 / number);
        if (single) {
            $('.o-tw-walls-col').addClass('o-tw-tweet-single');
        } else if (single === false) {
            $('.o-tw-walls-col').removeClass('o-tw-tweet-single');
        }
        if (newCols.length) {
            this.twitterWall.prependTweetsTo = newCols[0];
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Delete tweet
     *
     * @override
     * @param {Event} ev
     */
    _onDeleteTweet: function (ev) {
        var tweet = $(ev.target).closest('.o-tw-tweet');
        this.orm.unlink("website.twitter.tweet", [tweet.data('tweet-id')]).then(function (res) {
            if (res) {
                tweet.slideUp(500);
            }
        });
    },
    /**
     * Toggle Fullscreen
     *
     * @override
     */
    _onLiveButton: function () {
        if ((document.fullScreenElement && document.fullScreenElement !== null) || (!document.mozFullScreen && !document.webkitIsFullScreen)) {
            if (document.documentElement.requestFullScreen) {
                document.documentElement.requestFullScreen();
            } else if (document.documentElement.mozRequestFullScreen) {
                document.documentElement.mozRequestFullScreen();
            } else if (document.documentElement.webkitRequestFullScreen) {
                document.documentElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
            }
        } else {
            if (document.cancelFullScreen) {
                document.cancelFullScreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.webkitCancelFullScreen) {
                document.webkitCancelFullScreen();
            }
        }
    },
    /**
     * Handle all options
     *
     * @override
     * @param {Event} ev
     */
    _onOption: function (ev) {
        this.twitterWall.timeout = 7000;
        var $target = $(ev.currentTarget);
        var active = $target.hasClass('active');
        $target.toggleClass('active');
        switch ($target.data('operation')) {
            case 'list':
                $target.siblings().removeClass('active');
                this._setColumns(1);
                break;
            case 'double':
                $target.siblings().removeClass('active');
                this._setColumns(2);
                break;
            case 'triple':
                $target.siblings().removeClass('active');
                this._setColumns(3);
                break;
            case 'single':
                this._setColumns($('.o-tw-walls-col').length, !active);
                this.twitterWall.timeout = 15000;
                break;
            case 'repeat':
                this.twitterWall._toggleRepeat();
                break;
            case 'shuffle':
                this.twitterWall._toggleShuffle();
                break;
        }
        $(document).trigger('clear_tweet_queue');
    },
    /**
     * Handle zoom options
     *
     * @override
     * @param {Event} ev
     */
    _onZoom: function (ev) {
        var step = $(ev.currentTarget).data('operation') === 'plus' ? 0.05 : -0.05;
        this.twitterWall._zoom(this.twitterWall.zoomLevel + step);
    },
});
