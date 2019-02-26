odoo.define('website_rating.thread', function(require) {
    'use strict';

    var base = require('web_editor.base');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var rootWidget = require('web_editor.root_widget');

    var session = require('web.session');

    var qweb = core.qweb;
    var _t = core._t;

    var PortalComposer = require('portal.chatter').PortalComposer;
    var PortalChatter = require('portal.chatter').PortalChatter;

    var STAR_RATING_RATIO = 2;  // conversion factor from the star (1-5) to the db rating range (1-10)

    /**
     * PortalComposer
     *
     * Extends Frontend Composer to handle rating submission
     */
    PortalComposer.include({
        events: _.extend({}, PortalComposer.prototype.events, {
            "mousemove .stars i" : "_onMoveStar",
            "mouseleave .stars i" : "_onMoveOutStar",
            "click .stars" : "_onClickStar",
            "mouseleave .stars" : "_onMouseleaveStar",
        }),

        init: function(parent, options){
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
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                // rating stars
                self.$input = self.$('input[name="rating_value"]');
                self.$star_list = self.$('.stars').find('i');
                self.set("star_value", self.options.default_rating_value); // set the default value to trigger the display of star widget
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} event
         */
        _onClickStar: function(e){
            this.user_click = true;
            this.$input.val(this.get("star_value") * STAR_RATING_RATIO);
        },
        /**
         * @private
         */
        _onChangeStarValue: function(){
            var val = this.get("star_value");
            var index = Math.floor(val);
            var decimal = val - index;
            // reset the stars
            this.$star_list.removeClass('fa-star fa-star-half-o').addClass('fa-star-o');

            this.$('.stars').find("i:lt("+index+")").removeClass('fa-star-o fa-star-half-o').addClass('fa-star');
            if(decimal){
                this.$('.stars').find("i:eq("+(index)+")").removeClass('fa-star-o fa-star fa-star-half-o').addClass('fa-star-half-o');
            }
            this.$('.rate_text .badge').text(this.labels[index]);
        },
        _onMouseleaveStar: function(e){
            this.$('.rate_text').hide();
        },
        /**
         * @private
         * @param {MouseEvent} event
         */
        _onMoveStar: function(e){
            var index = this.$('.stars i').index(e.currentTarget);
            this.$('.rate_text').show();
            this.set("star_value", index+1);
        },
        /**
         * @private
         */
        _onMoveOutStar: function(){
            if(!this.user_click){
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
        }),
        xmlDependencies: (PortalChatter.prototype.xmlDependencies || []).concat(['/website_rating/static/src/xml/website_mail.xml', '/website_rating/static/src/xml/portal_chatter.xml']),

        init: function(parent, options){
            this._super.apply(this, arguments);
            // options
            if(!_.contains(this.options, 'display_rating')){
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
        willStart: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(result){
                // rating card
                if(result['rating_stats']){
                    var rating_data = {
                        'avg': Math.round(result['rating_stats']['avg'] / STAR_RATING_RATIO * 100) / 100,
                        'percent': [],
                    };
                    _.each(_.keys(result['rating_stats']['percent']), function(rating){

                        if (rating % 2 == 0) { // is even number
                            rating_data['percent'].push({
                                'num': rating / STAR_RATING_RATIO,
                                'percent': result['rating_stats']['percent'][rating],
                            });
                        }
                    });
                    self.set('rating_card_values', rating_data);
                }
            });
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
        preprocessMessages: function(messages){
            var self = this;
            var messages = this._super.apply(this, arguments);
            if(this.options['display_rating']){
                _.each(messages, function(m){
                    m['rating_value'] = self.round_to_half(m['rating_value'] / STAR_RATING_RATIO);
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
        round_to_half: function(value) {
            var converted = parseFloat(value); // Make sure we have a number
            var decimal = (converted - parseInt(converted, 10));
            decimal = Math.round(decimal * 10);
            if(decimal === 5){
                return (parseInt(converted, 10)+0.5);
            }
            if((decimal < 3) || (decimal > 7)){
                return Math.round(converted);
            }else{
                return (parseInt(converted, 10)+0.5);
            }
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _messageFetchPrepareParams: function(){
            var params = this._super.apply(this, arguments);
            if(this.options['display_rating']){
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
        _onClickStarDomain: function(e){
            var $tr = this.$(e.currentTarget);
            var num = $tr.data('star');
            if($tr.css('opacity') == 1){
                this.set('rating_value', num);
                this.$('.o_website_rating_select').css({
                    'opacity': 0.5,
                });
                this.$('.o_website_rating_select_text[data-star="'+num+'"]').css({
                    'visibility': 'visible',
                    'opacity': 1,
                });
                this.$('.o_website_rating_select[data-star="'+num+'"]').css({
                    'opacity': 1,
                });
            }
        },
        /**
         * @private
         * @param {MouseEvent} event
         */
        _onClickStarDomainReset: function(e){
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
        _onChangeRatingDomain: function(){
            var domain = [];
            if(this.get('rating_value')){
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
    var RatingPopupComposer = Widget.extend({
        template: 'website_rating.PopupComposer',
        xmlDependencies: [
            '/portal/static/src/xml/portal_chatter.xml',
            '/website_rating/static/src/xml/website_mail.xml',
            '/website_rating/static/src/xml/portal_chatter.xml',
        ],

        init: function(parent, options){
            this._super.apply(this, arguments);
            this.rating_avg = Math.round(options['ratingAvg'] / STAR_RATING_RATIO * 100) / 100 || 0.0;
            this.rating_total = options['ratingTotal'] || 0.0;

            this.options = _.defaults({}, options, {
                'token': false,
                'res_model': false,
                'res_id': false,
                'pid': 0,
                'display_composer': !session.is_website_user,
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

            return $.when.apply($, defs);
        },
    });


base.ready().then(function () {
    $('.o_rating_popup_composer').each(function (index) {
        var $elem = $(this);
        var rating_popup = new RatingPopupComposer(rootWidget, $elem.data());
        rating_popup.appendTo($elem);
    });
});


});
