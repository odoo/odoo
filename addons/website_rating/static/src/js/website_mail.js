odoo.define('website_rating.thread', function(require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');

    var qweb = core.qweb;
    var _t = core._t;

    var PortalChatter = require('portal.chatter').PortalChatter;

    /**
     * Extends Frontend Chatter to handle rating
     */
    PortalChatter.include({
        events: _.extend({}, PortalChatter.prototype.events, {
            "mousemove .stars i" : "_onMoveStar",
            "mouseleave .stars i" : "_onMoveOutStar",
            "click .stars" : "_onClickStar",
            "mouseleave .stars" : "_onMouseleaveStar",
            "click .o_website_rating_select": "_onClickStarDomain",
            "click .o_website_rating_select_text": "_onClickStarDomainReset",
        }),

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
            // rating star
            this.labels = {
                '0': "",
                '1': _t("I hate it"),
                '2': _t("I don't like it"),
                '3': _t("It's okay"),
                '4': _t("I like it"),
                '5': _t("I love it"),
            };
            this.user_click = false; // user has click or not
            this.set("star_value", this.options.rating_default_value);
            this.on("change:star_value", this, this._onChangeStarValue);
        },
        willStart: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(result){
                // rating card
                if(result['rating_stats']){
                    var rating_data = {
                        'avg': self.round_to_half(result['rating_stats']['avg']),
                        'percent': [],
                    };
                    _.each(_.keys(result['rating_stats']['percent']), function(rating){
                        if(0 < rating && rating <= 5){
                            rating_data['percent'].push({
                                'num': rating,
                                'percent': result['rating_stats']['percent'][rating],
                            });
                        }
                    });
                    self.set('rating_card_values', rating_data);
                }
            });
        },
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                // rating stars
                self.$input = self.$('input[name="rating_value"]');
                self.$star_list = self.$('.stars').find('i');
                self.set("star_value", self.options.rating_default_value); // set the default value to trigger the display of star widget
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
                    m['rating_value'] = self.round_to_half(m['rating_value']);
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

        _loadTemplates: function(){
            return $.when(this._super(), ajax.loadXML('/website_rating/static/src/xml/website_mail.xml', qweb));
        },
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
        _onClickStar: function(e){
            this.user_click = true;
            this.$input.val(this.get("star_value"));
        },
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
                domain = [['rating_value', '=', this.get('rating_value')]];
            }
            this._changeCurrentPage(1, domain);
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

            this.$('.rate_text .label').text(this.labels[index]);
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
});
