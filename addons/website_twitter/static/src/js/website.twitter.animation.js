/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import { escape } from "@web/core/utils/strings";

import { markup } from "@odoo/owl";

publicWidget.registry.twitter = publicWidget.Widget.extend({
    selector: '.twitter',
    disabledInEditableMode: false,
    events: {
        'mouseenter .wrap-row': '_onEnterRow',
        'mouseleave .wrap-row': '_onLeaveRow',
        'click .twitter_timeline .tweet': '_onTweetClick',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        var $timeline = this.$('.twitter_timeline');

        $timeline.append('<center><div><img src="/website_twitter/static/src/img/loadtweet.gif"></div></center>');
        var def = this.rpc('/website_twitter/get_favorites').then(function (data) {
            $timeline.empty();

            if (data.error) {
                $timeline.append(renderToElement('website.Twitter.Error', {data: data}));
                return;
            }

            if (Object.keys(data || {}).length === 0) {
                return;
            }

            var tweets = data.map((tweet) => {
                // Parse tweet date
                if (Object.keys(tweet.created_at || {}).length === 0) {
                    tweet.created_at = '';
                } else {
                    var v = tweet.created_at.split(' ');
                    var d = new Date(Date.parse(v[1]+' '+v[2]+', '+v[5]+' '+v[3]+' UTC'));
                    tweet.created_at = d.toDateString();
                }

                // Parse tweet text
                tweet.text = markup(escape(tweet.text)
                    .replace(
                        /[A-Za-z]+:\/\/[A-Za-z0-9-_]+\.[A-Za-z0-9-_:%&~\?\/.=]+/g,
                        function (url) {
                            return _makeLink(url, url);
                        }
                    )
                    .replace(
                        /[@]+[A-Za-z0-9_]+/g,
                        function (screen_name) {
                            return _makeLink('http://twitter.com/' + screen_name.replace('@', ''), screen_name);
                        }
                    )
                    .replace(
                        /[#]+[A-Za-z0-9_]+/g,
                        function (hashtag) {
                            return _makeLink('http://twitter.com/search?q=' + encodeURIComponent(hashtag.replace('#', '')), hashtag);
                        }
                    ));

                return renderToElement('website.Twitter.Tweet', {tweet: tweet});

                function _makeLink(url, text) {
                    return markup(`<a href="${url}" target="_blank" rel="noreferrer noopener">${text}</a>`);
                }
            });

            var f = Math.floor(tweets.length / 3);
            var tweetSlices = [tweets.slice(0, f).join(' '), tweets.slice(f, f * 2).join(' '), tweets.slice(f * 2, tweets.length).join(' ')];

            self.$scroller = $(renderToElement('website.Twitter.Scroller')).appendTo($timeline);
            self.$scroller.find('div[id^="scroller"]').toArray().forEach((element, index) => {
                var $scrollWrapper = $('<div/>', {class: 'scrollWrapper'});
                var $scrollableArea = $('<div/>', {class: 'scrollableArea'});
                $scrollWrapper.append($scrollableArea)
                              .data('scrollableArea', $scrollableArea);
                $scrollableArea.append(tweetSlices[index]);
                $(element).append($scrollWrapper);
                var totalWidth = 0;
                $scrollableArea.children().forEach((area) => {
                    totalWidth += $(area).outerWidth(true);
                });
                $scrollableArea.width(totalWidth);
                $scrollWrapper.scrollLeft(index*180);
            });
            self._startScrolling();
        });

        return Promise.all([this._super.apply(this, arguments), def]);
    },
    /**
     * @override
     */
    destroy: function () {
        this._stopScrolling();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _startScrolling: function () {
        if (!this.$scroller) {
            return;
        }
        this.$scroller.find('.scrollWrapper').toArray().forEach((el) => {
            var $wrapper = $(el);
            $wrapper.data('getNextElementWidth', true);
            $wrapper.data('autoScrollingInterval', setInterval(function () {
                $wrapper.scrollLeft($wrapper.scrollLeft() + 1);
                if ($wrapper.data('getNextElementWidth')) {
                    $wrapper.data('swapAt', $wrapper.data('scrollableArea').children(':first').outerWidth(true));
                    $wrapper.data('getNextElementWidth', false);
                }
                if ($wrapper.data('swapAt') <= $wrapper.scrollLeft()) {
                    var swap_el = $wrapper.data('scrollableArea').children(':first').detach();
                    $wrapper.data('scrollableArea').append(swap_el);
                    $wrapper.scrollLeft($wrapper.scrollLeft() - swap_el.outerWidth(true));
                    $wrapper.data('getNextElementWidth', true);
                }
            }, 20));
        });
    },
    /**
     * @private
     */
    _stopScrolling: function (wrapper) {
        if (!this.$scroller) {
            return;
        }
        this.$scroller.find('.scrollWrapper').toArray().forEach((el) => {
            var $wrapper = $(el);
            clearInterval($wrapper.data('autoScrollingInterval'));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onEnterRow: function () {
        this._stopScrolling();
    },
    /**
     * @private
     */
    _onLeaveRow: function () {
        this._startScrolling();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onTweetClick: function (ev) {
        if (ev.target.tagName === 'A') {
            return;
        }
        var url = $(ev.currentTarget).data('url');
        if (url) {
            window.open(url, '_blank');
        }
    },
});
