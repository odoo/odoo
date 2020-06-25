odoo.define('website_event_track.website_event_track_wishlist', function (require) {
'use strict';

var core = require('web.core');
var _t = core._t;
var publicWidget = require('web.public.widget');

publicWidget.registry.websiteEventTrackWishlistStar = publicWidget.Widget.extend({
    selector: '.o_wetrack_js_wishlist',
    events: {
        'click i': '_onWishlistToggleClick',
    },

    /**
     * @override
     * @private
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onWishlistToggleClick = _.debounce(this._onWishlistToggleClick, 500, true);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onWishlistToggleClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var $trackLink = $(ev.currentTarget);

        if (this.wishlisted === undefined) {
            this.wishlisted = $trackLink.data('wishlisted');
        }
        if (this.wishlistedByDefault === undefined) {
            this.wishlistedByDefault = $trackLink.data('wishlistedByDefault');
        }

        if (this.wishlistedByDefault) {
            this.displayNotification({
                type: 'info',
                title: _t('Key Track'),
                message: _.str.sprintf(_t('Key tracks are always wishlisted')),
            });
        }
        else {
            this._rpc({
                route: '/event/track/toggle_wishlist',
                params: {
                    track_id: $trackLink.data('trackId'),
                    set_wishlisted: !this.wishlisted
                },
            }).then(function (result) {
                if (result.error && result.error === 'ignored') {
                    self.displayNotification({
                        type: 'info',
                        title: _t('Please login'),
                        message: _.str.sprintf(_t('Unknown issue, please retry')),
                    });
                } else {
                    self.wishlisted = result.wishlisted;
                    self._updateDisplay();
                }
            });
        }
    },

    _updateDisplay: function () {
        var $trackLink = this.$el.find('i');
        if (this.wishlisted) {
            $trackLink.addClass('fa-star').removeClass('fa-star-o');
            $trackLink.attr('title', _t('Wishlisted'));
        } else {
            $trackLink.addClass('fa-star-o').removeClass('fa-star');
            $trackLink.attr('title', _t('Wishlist'));
        }
    },

});

return publicWidget.registry.websiteEventTrackWishlistStar;

});
