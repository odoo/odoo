odoo.define('rating.portal.chatter', function (require) {
'use strict';

var portalChatter = require('portal.chatter');
var utils = require('web.utils');

var PortalChatter = portalChatter.PortalChatter;

var STAR_RATING_RATIO = 2;  // conversion factor from the star (1-5) to the db rating range (1-10)

/**
 * PortalChatter
 *
 * Extends Frontend Chatter to handle rating
 */
PortalChatter.include({
    events: _.extend({}, PortalChatter.prototype.events, {
        "click .o_website_rating_select": "_onClickStarDomain",
        "click .o_website_rating_select_text": "_onClickStarDomainReset",
    }),
    xmlDependencies: (PortalChatter.prototype.xmlDependencies || [])
        .concat([
            '/website_rating/static/src/xml/portal_tools.xml',
            '/website_rating/static/src/xml/portal_chatter.xml'
        ]),

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        // options
        if (!_.contains(this.options, 'display_rating')) {
            this.options = _.defaults(this.options, {
                'display_rating': false,
                'rating_default_value': 0.0,
            });
        }
        // rating card
        this.set('rating_card_values', {});
        this.set('rating_value', false);
        this.on("change:rating_value", this, this._onChangeRatingDomain);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update the messages format
     *
     * @param {Array<Object>} messages
     * @returns {Array}
     */
    preprocessMessages: function (messages) {
        var self = this;
        messages = this._super.apply(this, arguments);
        if (this.options['display_rating']) {
            _.each(messages, function (m) {
                m['rating_value'] = self.roundToHalf(m['rating_value'] / STAR_RATING_RATIO);
            });
        }
        return messages;
    },
    /**
     * Round the given value with a precision of 0.5.
     *
     * Examples:
     * - 1.2 --> 1.0
     * - 1.7 --> 1.5
     * - 1.9 --> 2.0
     *
     * @param {Number} value
     * @returns Number
     **/
    roundToHalf: function (value) {
        var converted = parseFloat(value); // Make sure we have a number
        var decimal = (converted - parseInt(converted, 10));
        decimal = Math.round(decimal * 10);
        if (decimal === 5) {
            return (parseInt(converted, 10) + 0.5);
        }
        if ((decimal < 3) || (decimal > 7)) {
            return Math.round(converted);
        } else {
            return (parseInt(converted, 10) + 0.5);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _chatterInit: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function (result) {
            if (!result['rating_stats']) {
                return;
            }
            var ratingData = {
                'avg': Math.round(result['rating_stats']['avg'] / STAR_RATING_RATIO * 100) / 100,
                'percent': [],
            };
            _.each(_.keys(result['rating_stats']['percent']).reverse(), function (rating) {
                if (rating % 2 === 0) {
                    ratingData['percent'].push({
                        'num': rating / STAR_RATING_RATIO,
                        'percent': utils.round_precision(result['rating_stats']['percent'][rating], 0.01),
                    });
                }
            });
            self.set('rating_card_values', ratingData);
        });
    },
    /**
     * @override
     */
    _messageFetchPrepareParams: function () {
        var params = this._super.apply(this, arguments);
        if (this.options['display_rating']) {
            params['rating_include'] = true;
        }
        return params;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickStarDomain: function (e) {
        var $tr = this.$(e.currentTarget);
        var num = $tr.data('star');
        if ($tr.css('opacity') === '1') {
            this.set('rating_value', num);
            this.$('.o_website_rating_select').css({
                'opacity': 0.5,
            });
            this.$('.o_website_rating_select_text[data-star="' + num + '"]').css({
                'visibility': 'visible',
                'opacity': 1,
            });
            this.$('.o_website_rating_select[data-star="' + num + '"]').css({
                'opacity': 1,
            });
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onClickStarDomainReset: function (e) {
        e.stopPropagation();
        e.preventDefault();
        this.set('rating_value', false);
        this.$('.o_website_rating_select_text').css('visibility', 'hidden');
        this.$('.o_website_rating_select').css({
            'opacity': 1,
        });
    },
    /**
     * @private
     */
    _onChangeRatingDomain: function () {
        var domain = [];
        if (this.get('rating_value')) {
            domain = [['rating_value', '=', this.get('rating_value') * STAR_RATING_RATIO]];
        }
        this._changeCurrentPage(1, domain);
    },
});
});
