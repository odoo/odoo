
odoo.define('rating.rating', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var Widget = require('web.Widget');
    var translation = require('web.translation');
    var _t = translation._t;

    var labels = {
        '0' : "",
        '1' : _t("I hate it"),
        '2' : _t("I don't like it"),
        '3' : _t("It's okay"),
        '4' : _t("I like it"),
        '5' : _t("I love it"),
    };
    var page_widgets = {};

    $(document).ready(function(){

        // Rating Card
        $('[data-toggle="rating-popover"]').popover({
            html : true,
            trigger: 'hover',
            title: function() {
                return $($(this).data('popover-selector')).find('.popover-title').html();
            },
            content: function() {
              return $($(this).data('popover-selector')).find('.popover-content').html();
            }
        });

        // Star Widget
        var RatingStarWidget = Widget.extend({
            events: {
                "mousemove .stars i" : "moveOnStars",
                "mouseleave .stars i" : "moveOut",
                "click .stars" : "clickOnStar",
            },
            _setup: function(){
                this.$input = this.$('input');
                this.star_list = this.$('.stars').find('i');

                this.is_editable = !this.$input.data('is_disabled');
                this.fixed = false; // user has click or not
                // set the default value and bind event
                var default_value = this.$input.data('default') || -1;
                default_value = this.roundToHalf(default_value);
                this.set("star_value", default_value);
                this.on("change:star_value", this, this.changeStars);
            },
            setElement: function($el){
                this._super.apply(this, arguments);
                this._setup();
            },
            changeStars: function(){
                var val = this.get("star_value");
                var index = Math.floor(val);
                var decimal = val - index;
                // reset the stars
                this.star_list.removeClass('fa-star fa-star-half-o').addClass('fa-star-o');
                if(index >= 0){
                    this.$('.stars').find("i:lt("+index+")").removeClass('fa-star-o fa-star-half-o').addClass('fa-star');
                    if(decimal){
                        this.$('.stars').find("i:eq("+(index)+")").removeClass('fa-star-o fa-star fa-star-half-o').addClass('fa-star-half-o');
                    }
                }else{
                    val = 0.0;
                }
                this.$input.val(val);
                this.$('.rate_text .label').text(labels[index]);
            },
            moveOut: function(){
                if(!this.fixed && this.is_editable){
                    this.set("star_value", -1);
                }
                this.fixed = false;
            },
            moveOnStars: function(e){
                if(this.is_editable){
                    var index = this.$('.stars i').index(e.currentTarget);
                    this.set("star_value", index+1);
                }
            },
            clickOnStar: function(e){
                if(this.is_editable){
                    this.fixed = true;
                }
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

        $('.o_rating_star_card').each(function(index, elem){
            page_widgets[index] = new RatingStarWidget().setElement(elem);
        })

    });

    return {
        rating_star_widgets : page_widgets
    };
});