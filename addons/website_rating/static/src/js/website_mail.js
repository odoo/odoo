odoo.define('website_rating.thread', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var session = require('web.session');
var portalChatter = require('portal.chatter');
var utils = require('web.utils');
var time = require('web.time');

var _t = core._t;
var qweb = core.qweb;


var PortalComposer = portalChatter.PortalComposer;
var PortalChatter = portalChatter.PortalChatter;

var STAR_RATING_RATIO = 2; // conversion factor from the star (1-5) to the db rating range (1-10)

/**
 * PortalComposer
 *
 * Extends Frontend Composer to handle rating submission
 */
PortalComposer.include({
    events: _.extend({}, PortalComposer.prototype.events, {
        "mousemove .stars i": "_onMoveStar",
        "mouseleave .stars i": "_onMoveOutStar",
        "click .stars": "_onClickStar",
        "mouseleave .stars": "_onMouseleaveStar",
    }),

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        // apply ratio to default rating value
        if (options.default_rating_value) {
            options.default_rating_value = parseFloat(options.default_rating_value) / STAR_RATING_RATIO;
        }

        // default options
        this.options = _.defaults(this.options, {
            'default_message': false,
            'default_message_id': false,
            'default_rating_value': false,
            'force_submit_url': false,
        });
        // star input widget
        this.labels = {
            '0': "",
            '1': _t("I hate it"),
            '2': _t("I don't like it"),
            '3': _t("It's okay"),
            '4': _t("I like it"),
            '5': _t("I love it"),
        };
        this.user_click = false; // user has click or not
        this.set("star_value", this.options.default_rating_value);
        this.on("change:star_value", this, this._onChangeStarValue);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // rating stars
            self.$input = self.$('input[name="rating_value"]');
            self.$star_list = self.$('.stars').find('i');

            // set the default value to trigger the display of star widget and update the hidden input value.
            self.set("star_value", self.options.default_rating_value); 
            self.$input.val(self.options.default_rating_value * STAR_RATING_RATIO);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickStar: function () {
        this.user_click = true;
        this.$input.val(this.get("star_value") * STAR_RATING_RATIO);
    },
    /**
     * @private
     */
    _onChangeStarValue: function () {
        var val = this.get("star_value");
        var index = Math.floor(val);
        var decimal = val - index;
        // reset the stars
        this.$star_list.removeClass('fa-star fa-star-half-o').addClass('fa-star-o');

        this.$('.stars').find("i:lt(" + index + ")").removeClass('fa-star-o fa-star-half-o').addClass('fa-star');
        if (decimal) {
            this.$('.stars').find("i:eq(" + index + ")").removeClass('fa-star-o fa-star fa-star-half-o').addClass('fa-star-half-o');
        }
        this.$('.rate_text .badge').text(this.labels[index]);
    },
    /**
     * @private
     */
    _onMouseleaveStar: function () {
        this.$('.rate_text').hide();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMoveStar: function (ev) {
        var index = this.$('.stars i').index(ev.currentTarget);
        this.$('.rate_text').show();
        this.set("star_value", index + 1);
    },
    /**
     * @private
     */
    _onMoveOutStar: function () {
        if (!this.user_click) {
            this.set("star_value", parseInt(this.$input.val()));
        }
        this.user_click = false;
    },
});

/**
 * PortalChatter
 *
 * Extends Frontend Chatter to handle rating
 */
PortalChatter.include({
    events: _.extend({}, PortalChatter.prototype.events, {
        "click .o_website_rating_select": "_onClickStarDomain",
        "click .o_website_rating_select_text": "_onClickStarDomainReset",
        "click .o_website_publisher_comment": "_onClickPublisherEditComment",
        "click .o_website_publisher_comment_edit": "_onClickPublisherEditComment",
        "click .o_website_publisher_comment_delete": "_onClickPublisherDeleteComment",
        "click .o_website_publisher_comment_submit": "_onClickPublisherCommentSubmit",
        "click .o_website_publisher_comment_cancel": "_onClickPublisherCommentCancel",
    }),
    xmlDependencies: (PortalChatter.prototype.xmlDependencies || [])
        .concat([
            '/website_rating/static/src/xml/website_mail.xml',
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
            _.each(messages, function (m, i) {
                m['rating_value'] = self.roundToHalf(m['rating_value'] / STAR_RATING_RATIO);

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

    /**
     * Default rating data for publisher comment qweb template
     * @private
     * @param {Integer} messageIndex 
     */
    _newPublisherCommentData: function (messageIndex) {
        return {
            mes_index: messageIndex,
            publisher_id: this.options.partner_id,
            publisher_avatar: _.str.sprintf('/web/image/%s/%s/image_64/50x50', 'res.partner', this.options.partner_id),
            publisher_name: _t("Write your comment"),
            publisher_date: '',
            publisher_comment: '',
            publisher_comment_plaintext: ''
        };
    }, 

     /**
     * preprocess the rating data comming from /website/rating/comment or the chatter_init
     * Can be also use to have new rating data for a new publisher comment
     * @param {JSON} rawRating 
     * @returns {JSON} the process rating data
     */
    _preprocessCommentData: function (rawRating, messageIndex) {
        var newData = {
            id: rawRating.id,
            mes_index: messageIndex,
            publisher_date: rawRating.publisher_date ? _.str.sprintf(_t('Published on %s'), moment(time.str_to_datetime(rawRating.publisher_date)).format('MMMM Do YYYY, h:mm:ss a')) : "",
            publisher_comment: rawRating.publisher_comment ? rawRating.publisher_comment : '',
            publisher_comment_plaintext: rawRating.publisher_comment_plaintext ? rawRating.publisher_comment_plaintext : '',
        };

        // split array (id, display_name) of publisher_id into publisher_id and publisher_name
        if (rawRating.publisher_id && rawRating.publisher_id.length >= 2) {
            newData.publisher_name = rawRating.publisher_id[1];
            newData.publisher_id = rawRating.publisher_id[0];
            newData.publisher_avatar = _.str.sprintf('/web/image/%s/%s/image_64/50x50', 'res.partner', newData.publisher_id);
        } 
        newData = _.defaults(newData, rawRating);
        newData = _.defaults(newData, this._newPublisherCommentData(messageIndex));

        return newData;
    },

    /** ---------------
     * Selection of elements for the publisher comment feature
     * Only available from a source in a publisher_comment or publisher_comment_form template
     */

    _getCommentContainer: function ($source) {
        return $source.parents(".o_website_publisher_comment_container_global").first().find(".o_website_publisher_comment_container").first();
    },

    _getCommentButton: function ($source) {
        return $source.parents(".o_website_publisher_comment_container_global").first().find(".o_website_publisher_comment").first();
    },

    _getCommentTextarea: function ($source) {
        return $source.parents(".o_website_publisher_comment_container_global").first().find(".o_portal_rating_comment_input").first();
    },

    _focusTextComment: function ($source) {
        this._getCommentTextarea($source).focus();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickStarDomain: function (ev) {
        var $tr = this.$(ev.currentTarget);
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
     * @param {MouseEvent} ev
     */
    _onClickStarDomainReset: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.set('rating_value', false);
        this.$('.o_website_rating_select_text').css('visibility', 'hidden');
        this.$('.o_website_rating_select').css({
            'opacity': 1,
        });
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPublisherEditComment: function (ev) {
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
        data.rating.publisher_comment_plaintext = oldRating.publisher_comment_plaintext ? oldRating.publisher_comment_plaintext : '';
        data.rating.publisher_comment = oldRating.publisher_comment ? oldRating.publisher_comment : '';
        this._getCommentContainer($source).html($(qweb.render("website_rating.publisher_comment_form", data)));
        this._focusTextComment($source);
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPublisherDeleteComment: function (ev) {
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
                self._getCommentContainer($source).html($(qweb.render("website_rating.publisher_comment", { 
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
            this._getCommentContainer($source).html($(qweb.render("website_rating.publisher_comment", data)));
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
            domain = [['rating_value', '=', this.get('rating_value') * STAR_RATING_RATIO]];
        }
        this._changeCurrentPage(1, domain);
    },
});

/**
 * RatingPopupComposer
 *
 * Display the rating average with a static star widget, and open
 * a popup with the portal composer when clicking on it.
 **/
var RatingPopupComposer = publicWidget.Widget.extend({
    template: 'website_rating.PopupComposer',
    xmlDependencies: [
        '/portal/static/src/xml/portal_chatter.xml',
        '/website_rating/static/src/xml/website_mail.xml',
        '/website_rating/static/src/xml/portal_chatter.xml',
    ],

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.rating_avg = Math.round(options['ratingAvg'] / STAR_RATING_RATIO * 100) / 100 || 0.0;
        this.rating_total = options['ratingTotal'] || 0.0;

        this.options = _.defaults({}, options, {
            'token': false,
            'res_model': false,
            'res_id': false,
            'pid': 0,
            'display_composer': options['disable_composer'] ? false : !session.is_website_user,
            'display_rating': true,
            'csrf_token': odoo.csrf_token,
            'user_id': session.user_id,
        });
    },
    /**
     * @override
     */
    start: function () {
        var defs = [];
        defs.push(this._super.apply(this, arguments));

        // instanciate and insert composer widget
        this._composer = new PortalComposer(this, this.options);
        defs.push(this._composer.replace(this.$('.o_portal_chatter_composer')));

        return Promise.all(defs);
    },
});

publicWidget.registry.RatingPopupComposer = publicWidget.Widget.extend({
    selector: '.o_rating_popup_composer',

    /**
     * @override
     */
    start: function () {
        var ratingPopup = new RatingPopupComposer(this, this.$el.data());
        return Promise.all([
            this._super.apply(this, arguments),
            ratingPopup.appendTo(this.$el)
        ]);
    },
});
});
