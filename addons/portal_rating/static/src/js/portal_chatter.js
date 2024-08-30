odoo.define('rating.portal.chatter', function (require) {
'use strict';

var core = require('web.core');
var portalChatter = require('portal.chatter');
var utils = require('web.utils');
var time = require('web.time');

var _t = core._t;
var PortalChatter = portalChatter.PortalChatter;
var qweb = core.qweb;

/**
 * PortalChatter
 *
 * Extends Frontend Chatter to handle rating
 */
PortalChatter.include({
    events: _.extend({}, PortalChatter.prototype.events, {
        // star based control
        'click .o_website_rating_table_row': '_onClickStarDomain',
        'click .o_website_rating_selection_reset': '_onClickStarDomainReset',
        // publisher comments
        'click .o_wrating_js_publisher_comment_btn': '_onClickPublisherComment',
        'click .o_wrating_js_publisher_comment_edit': '_onClickPublisherComment',
        'click .o_wrating_js_publisher_comment_delete': '_onClickPublisherCommentDelete',
        'click .o_wrating_js_publisher_comment_submit': '_onClickPublisherCommentSubmit',
        'click .o_wrating_js_publisher_comment_cancel': '_onClickPublisherCommentCancel',
    }),
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
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.on("change:rating_card_values", this, this._renderRatingCard);
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
            _.each(messages, function (m, i) {
                m.rating_value = self.roundToHalf(m['rating_value']);
                m.rating = self._preprocessCommentData(m.rating, i);
            });
        }
        // save messages in the widget to process correctly the publisher comment templates
        this.messages = messages;
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
     * @returns {Promise}
     */
    _chatterInit: async function () {
        const result = await this._super(...arguments);
        this._updateRatingCardValues(result);
        return result;
    },
    /**
     * @override
     * @param {Array} domain
     * @returns {Promise}
     */
    messageFetch: async function (domain) {
        const result = await this._super(...arguments);
        this._updateRatingCardValues(result);
        return result;
    },
    /**
     * Calculates and Updates rating values i.e. average, percentage
     *
     * @private
     */
    _updateRatingCardValues: function (result) {
        if (!result['rating_stats']) {
            return;
        }
        const self = this;
        const ratingData = {
            'avg': Math.round(result['rating_stats']['avg'] * 100) / 100,
            'percent': [],
        };
        _.each(_.sortBy(_.keys(result['rating_stats']['percent'])).reverse(), function (rating) {
            ratingData['percent'].push({
                'num': self.roundToHalf(rating),
                'percent': utils.round_precision(result['rating_stats']['percent'][rating], 0.01),
            });
        });
        this.set('rating_card_values', ratingData);
    },
    /**
     * @override
     */
    _messageFetchPrepareParams: function () {
        var params = this._super.apply(this, arguments);
        if (this.options['display_rating']) {
            params['rating_include'] = true;

            const ratingValue = this.get('rating_value');
            if (ratingValue !== false) {
                params['rating_value'] = ratingValue;
            }
        }
        return params;
    },

    /**
     * render rating card
     *
     * @private
     */
    _renderRatingCard: function () {
        this.$('.o_website_rating_card_container').replaceWith(qweb.render("portal_rating.rating_card", {widget: this}));
    },
    /**
     * Default rating data for publisher comment qweb template
     * @private
     * @param {Integer} messageIndex 
     */
    _newPublisherCommentData: function (messageIndex) {
        return {
            mes_index: messageIndex,
            publisher_id: this.options.partner_id,
            publisher_avatar: _.str.sprintf('/web/image/res.partner/%s/avatar_128/50x50', this.options.partner_id),
            publisher_name: _t("Write your comment"),
            publisher_datetime: '',
            publisher_comment: '',
        };
    }, 

     /**
     * preprocess the rating data comming from /website/rating/comment or the chatter_init
     * Can be also use to have new rating data for a new publisher comment
     * @param {JSON} rawRating 
     * @returns {JSON} the process rating data
     */
    _preprocessCommentData: function (rawRating, messageIndex) {
        var ratingData = {
            id: rawRating.id,
            mes_index: messageIndex,
            publisher_datetime: rawRating.publisher_datetime ? moment(time.str_to_datetime(rawRating.publisher_datetime)).format('MMMM Do YYYY, h:mm:ss a') : "",
            publisher_comment: rawRating.publisher_comment ? rawRating.publisher_comment : '',
        };

        // split array (id, display_name) of publisher_id into publisher_id and publisher_name
        if (rawRating.publisher_id && rawRating.publisher_id.length >= 2) {
            ratingData.publisher_id = rawRating.publisher_id[0];
            ratingData.publisher_name = rawRating.publisher_id[1];
            ratingData.publisher_avatar = _.str.sprintf('/web/image/res.partner/%s/avatar_128/50x50', ratingData.publisher_id);
        }
        var commentData = _.extend(this._newPublisherCommentData(messageIndex), ratingData);
        return commentData;
    },

    /** ---------------
     * Selection of elements for the publisher comment feature
     * Only available from a source in a publisher_comment or publisher_comment_form template
     */

    _getCommentContainer: function ($source) {
        return $source.parents(".o_wrating_publisher_container").first().find(".o_wrating_publisher_comment").first();
    },

    _getCommentButton: function ($source) {
        return $source.parents(".o_wrating_publisher_container").first().find(".o_wrating_js_publisher_comment_btn").first();
    },

    _getCommentTextarea: function ($source) {
        return $source.parents(".o_wrating_publisher_container").first().find(".o_portal_rating_comment_input").first();
    },

    _focusTextComment: function ($source) {
        this._getCommentTextarea($source).focus();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Show a spinner and hide messages during loading.
     *
     * @override
     * @returns {Promise}
     */
    _onChangeDomain: function () {
        const spinnerDelayed = setTimeout(()=> {
            this.$('.o_portal_chatter_messages_loading').removeClass('d-none');
            this.$('.o_portal_chatter_messages').addClass('d-none');
        }, 500);
        return this._super.apply(this, arguments).finally(()=>{
            clearTimeout(spinnerDelayed);
            // Hide spinner and show messages
            this.$('.o_portal_chatter_messages_loading').addClass('d-none');
            this.$('.o_portal_chatter_messages').removeClass('d-none');
        });
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickStarDomain: function (ev) {
        var $tr = this.$(ev.currentTarget);
        var num = $tr.data('star');
        this.set('rating_value', num);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickStarDomainReset: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.set('rating_value', false);
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPublisherComment: function (ev) {
        var $source = this.$(ev.currentTarget);
        // If the form is already present => like cancel remove the form
        if (this._getCommentTextarea($source).length === 1) {
            this._getCommentContainer($source).empty();
            return;
        }
        var messageIndex = $source.data("mes_index");
        var data = {is_publisher: this.options['is_user_publisher']}; 
        data.rating = this._newPublisherCommentData(messageIndex);
        
        var oldRating = this.messages[messageIndex].rating;
        data.rating.publisher_comment = oldRating.publisher_comment ? oldRating.publisher_comment : '';
        this._getCommentContainer($source).html($(qweb.render("portal_rating.chatter_rating_publisher_form", data)));
        this._focusTextComment($source);
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPublisherCommentDelete: function (ev) {
        var self = this;
        var $source = this.$(ev.currentTarget);

        var messageIndex = $source.data("mes_index");
        var ratingId = this.messages[messageIndex].rating.id;

        this._rpc({
            route: '/website/rating/comment',
            params: {
                "rating_id": ratingId,
                "publisher_comment": '' // Empty publisher comment means no comment
            }
        }).then(function (res) {
            self.messages[messageIndex].rating = self._preprocessCommentData(res, messageIndex);
            self._getCommentButton($source).removeClass("d-none");
            self._getCommentContainer($source).empty();
        });
    },  

     /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPublisherCommentSubmit: function (ev) {
        var self = this;
        var $source = this.$(ev.currentTarget);

        var messageIndex = $source.data("mes_index");
        var comment = this._getCommentTextarea($source).val();
        var ratingId = this.messages[messageIndex].rating.id;

        this._rpc({
            route: '/website/rating/comment',
            params: {
                "rating_id": ratingId,
                "publisher_comment": comment
            }
        }).then(function (res) {

            // Modify the related message
            self.messages[messageIndex].rating = self._preprocessCommentData(res, messageIndex);
            if (self.messages[messageIndex].rating.publisher_comment !== '') {
                // Remove the button comment if exist and render the comment
                self._getCommentButton($source).addClass('d-none');
                self._getCommentContainer($source).html($(qweb.render("portal_rating.chatter_rating_publisher_comment", { 
                    rating: self.messages[messageIndex].rating,
                    is_publisher: self.options.is_user_publisher
                })));
            } else {
                // Empty string or false considers as no comment
                self._getCommentButton($source).removeClass("d-none");
                self._getCommentContainer($source).empty();       
            }
        });
    },

     /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPublisherCommentCancel: function (ev) {
        var $source = this.$(ev.currentTarget);
        var messageIndex = $source.data("mes_index");

        var comment = this.messages[messageIndex].rating.publisher_comment;
        if (comment) {
            var data = {
                rating: this.messages[messageIndex].rating,
                is_publisher: this.options.is_user_publisher
            };
            this._getCommentContainer($source).html($(qweb.render("portal_rating.chatter_rating_publisher_comment", data)));
        } else {
            this._getCommentContainer($source).empty();
        }
    },

    /**
     * @private
     */
    _onChangeRatingDomain: function () {
        var domain = [];
        if (this.get('rating_value')) {
            // TODO dead code: remove in master
            domain = [['rating_value', '=', this.get('rating_value')]];
        }
        this._changeCurrentPage(1, domain);
    },
});
});
