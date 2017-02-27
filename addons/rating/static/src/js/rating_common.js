odoo.define('rating.rating', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var translation = require('web.translation');
    var _t = translation._t;

    // Star Widget
    var RatingStarWidget = Widget.extend({
        template: 'rating.rating_star_card',
        events: {
            "mousemove .stars i" : "moveOnStars",
            "mouseleave .stars i" : "moveOut",
            "click .stars" : "clickOnStar",
            "mouseleave .stars" : "moveOutStars",
        },
        init: function(parent, options){
            this._super.apply(this, arguments);
            this.options = _.defaults(options || {}, {
                'rating_default_value': 0,
                'rating_disabled': 0,
            });
            this.labels = {
                '0': "",
                '1': _t("I hate it"),
                '2': _t("I don't like it"),
                '3': _t("It's okay"),
                '4': _t("I like it"),
                '5': _t("I love it"),
            };
            this.user_click = false; // user has click or not
            this.set("star_value", 0);
            this.on("change:star_value", this, this.changeStars);
        },
        start: function(){
            this.$input = this.$('input');
            this.star_list = this.$('.stars').find('i');
            // set the default value
            this.set("star_value", this.options.rating_default_value);
            this.is_editable = !this.options.rating_disabled;
        },
        attachTo: function(el){
            this._super.apply(this, arguments);
            // set the default value and bind event
            var default_value = this.$('input').data('default') || this.options['rating_default_value'];
            default_value = this.roundToHalf(default_value);
            this.set('star_value', default_value);
            // is_editable value from DOM
            this.is_editable = !this.$input.data('is_disabled') || this.options['rating_disabled'];
        },
        changeStars: function(){
            var val = this.get("star_value");
            var index = Math.floor(val);
            var decimal = val - index;
            // reset the stars
            this.star_list.removeClass('fa-star fa-star-half-o').addClass('fa-star-o');

            this.$('.stars').find("i:lt("+index+")").removeClass('fa-star-o fa-star-half-o').addClass('fa-star');
            if(decimal){
                this.$('.stars').find("i:eq("+(index)+")").removeClass('fa-star-o fa-star fa-star-half-o').addClass('fa-star-half-o');
            }

            this.$input.val(val);
            this.$('.rate_text .label').text(this.labels[index]);
        },
        moveOut: function(){
            if(!this.user_click && this.is_editable){
                this.set("star_value", 0);
            }
            this.user_click = false;
        },
        moveOnStars: function(e){
            if(this.is_editable){
                this.$('.rate_text').show();
                var index = this.$('.stars i').index(e.currentTarget);
                this.set("star_value", index+1);
            }
        },
        clickOnStar: function(e){
            if(this.is_editable){
                this.user_click = true;
            }
        },
        moveOutStars: function(e){
            this.$('.rate_text').hide();
        },
        roundToHalf: function(value) {
            var converted = parseFloat(value); // Make sure we have a number
            var decimal = (converted - parseInt(converted, 10));
            decimal = Math.round(decimal * 10);
            if(decimal == 5){
                return (parseInt(converted, 10)+0.5);
            }
            if((decimal < 3) || (decimal > 7)){
                return Math.round(converted);
            }else{
                return (parseInt(converted, 10)+0.5);
            }
        },
    });

    var page_widgets = {};

    $(document).ready(function(){
        // Rating Card
        $('[data-toggle="rating-popover"]').popover({
            html : true,
            trigger: 'hover',
            title: function() {
                return $(this).parent().find('.rating_popover').find('.popover-title').html();
            },
            content: function() {
              return $(this).parent().find('.rating_popover').find('.popover-content').html();
            }
        });
        // Rating Star Widget instances
        $('.o_rating_star_card').each(function(index, elem){
            page_widgets[index] = new RatingStarWidget();
            page_widgets[index].attachTo(elem);
        })
    });

    return {
        RatingStarWidget: RatingStarWidget,
        rating_star_widgets: page_widgets,
    };
});