/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import { escape } from "@web/core/utils/strings";
import { rpc } from "@web/core/network/rpc";

import { markup } from "@odoo/owl";

publicWidget.registry.twitter = publicWidget.Widget.extend({
    selector: '.twitter',
    disabledInEditableMode: false,
    events: {
        'mouseenter .wrap-row': '_onEnterRow',
        'mouseleave .wrap-row': '_onLeaveRow',
        'click .twitter_timeline .tweet': '_onTweetClick',
    },

    /**
     * @override
     */
    start: function () {
        const self = this;
        let timeline = this.el.querySelector('.twitter_timeline');

        const newElement = document.createElement('center');
        newElement.innerHTML = '<div><img src="/website_twitter/static/src/img/loadtweet.gif"></div>';
        timeline.appendChild(newElement);
        const def = rpc('/website_twitter/get_favorites').then(function (data) {
            timeline.innerHTML = '';

            if (data.error) {
                timeline.append(renderToElement('website.Twitter.Error', {data: data}));
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

            let f = Math.floor(tweets.length / 3);
            let tweetSlices = [tweets.slice(0, f).join(' '), tweets.slice(f, f * 2).join(' '), tweets.slice(f * 2, tweets.length).join(' ')];

            self.scroller = timeline.appendChild(renderToElement('website.Twitter.Scroller'));
            [...self.scroller.querySelectorAll('div[id^="scroller"]')].forEach((element, index) => {
                const scrollWrapper = document.createElement('div');
                scrollWrapper.className = 'scrollWrapper';
                const scrollableArea = document.createElement('div');
                scrollableArea.className = 'scrollableArea';
                scrollWrapper.appendChild(scrollableArea);
                scrollWrapper.dataset.scrollableArea = scrollableArea;;
                scrollableArea.append(tweetSlices[index]);
                element.append(scrollWrapper);
                let totalWidth = 0;
                scrollableArea.childNodes.forEach((area) => {
                    // TODO_VISP: debug this as i'm not sure
                    totalWidth += area.offsetWidth + parseFloat(window.getComputedStyle(area).marginLeft) + parseFloat(window.getComputedStyle(area).marginRight);
                });
                scrollableArea.style.width = totalWidth;
                // TODO-VISP: debug this as we need to create method
                scrollWrapper.scrollLeft = index * 180;
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
        if (!this.scroller) {
            return;
        }
        [...this.scroller.querySelectorAll('.scrollWrapper')].forEach((el) => {
            const wrapper = el;
            wrapper.dataset.getNextElementWidth = true;
            wrapper.dataset.autoScrollingInterval = setInterval(function () {
                const firstChild = wrapper.querySelector('.scrollableArea').firstElementChild;
                wrapper.scrollLeft = wrapper.scrollLeft + 1;
                if (wrapper.dataset.getNextElementWidth) {
                    // TODO_VISP: debug this as we need to create method
                    const totalWidth = firstChild.offsetWidth + parseFloat(window.getComputedStyle(firstChild).marginLeft) + parseFloat(window.getComputedStyle(firstChild).marginRight);
                    wrapper.dataset.swapAt = totalWidth;
                    wrapper.dataset.getNextElementWidth = false;
                }
                if (wrapper.dataset.swapAt <= wrapper.scrollLeft) {
                    const swap_el = firstChild.remove();
                    wrapper.querySelector('.scrollableArea').append(swap_el);
                    wrapper.scrollLeft = (wrapper.scrollLeft - swap_el.offsetWidth + parseFloat(window.getComputedStyle(swap_el).marginLeft) + parseFloat(window.getComputedStyle(swap_el).marginRight));
                    wrapper.dataset.getNextElementWidth = true;
                }
            }, 20);
        });
    },
    /**
     * @private
     */
    _stopScrolling: function (wrapper) {
        if (!this.scroller) {
            return;
        }
        [...this.scroller.querySelectorAll('.scrollWrapper')].forEach((el) => {
            const wrapper = el;
            clearInterval(wrapper.dataset.autoScrollingInterval);
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
        var url = ev.currentTarget.dataset.url;
        if (url) {
            window.open(url, '_blank');
        }
    },
});
