odoo.define('rating.portal.composer', function (require) {
'use strict';

var core = require('web.core');
var portalComposer = require('portal.composer');

var _t = core._t;

var PortalComposer = portalComposer.PortalComposer;

/**
 * PortalComposer
 *
 * Extends Portal Composer to handle rating submission
 */
PortalComposer.include({
    events: _.extend({}, PortalComposer.prototype.events, {
        'click .stars i': '_onClickStar',
        'mouseleave .stars': '_onMouseleaveStarBlock',
        'mousemove .stars i': '_onMoveStar',
        'mouseleave .stars i': '_onMoveLeaveStar',
    }),

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        // apply ratio to default rating value
        if (options.default_rating_value) {
            options.default_rating_value = parseFloat(options.default_rating_value);
        }

        // default options
        this.options = _.defaults(this.options, {
            'default_message': false,
            'default_message_id': false,
            'default_rating_value': 0.0,
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
            self.$input.val(self.options.default_rating_value);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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
    _onClickStar: function (ev) {
        var index = this.$('.stars i').index(ev.currentTarget);
        this.set("star_value", index + 1);
        this.user_click = true;
        this.$input.val(this.get("star_value"));
    },
    /**
     * @private
     */
    _onMouseleaveStarBlock: function () {
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
    _onMoveLeaveStar: function () {
        if (!this.user_click) {
            this.set("star_value", parseInt(this.$input.val()));
        }
        this.user_click = false;
    },
});
});
