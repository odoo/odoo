odoo.define('portal.rating.composer', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var session = require('web.session');
var portalComposer = require('portal.composer');

var PortalComposer = portalComposer.PortalComposer;
var _t = core._t;

var STAR_RATING_RATIO = 2;  // conversion factor from the star (1-5) to the db rating range (1-10)

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
        '/website_rating/static/src/xml/portal_tools.xml',
        '/website_rating/static/src/xml/portal_rating_composer.xml',
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
        var ratingPopupData = this.$el.data();
        var ratingPopup = new RatingPopupComposer(this, ratingPopupData);
        return Promise.all([
            this._super.apply(this, arguments),
            ratingPopup.appendTo(this.$el)
        ]);
    },
});

var RatingSelector = publicWidget.Widget.extend({
    template: 'website_rating.rating_star_input',
    xmlDependencies: ['/website_rating/static/src/xml/portal_tools.xml'],
    events: {
        'click .stars': '_onClickStarBlock',
        'click .refresh': '_onClickRefresh',
        'mouseleave .stars': '_onMouseleaveStarBlock',
        'mousemove .stars i': '_onMoveStar',
        'mouseleave .stars i': '_onMoveLeaveStar',
    },

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
        this.options = _.defaults(options || {}, {
            'default_message': false,
            'default_message_id': false,
            'default_rating_value': false,
            'force_submit_url': false,
            'display_badge': true,
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
            self.$refresh = self.$('.refresh');

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
        if (this.options.display_badge) {
            this.$('.rate_text .badge').text(this.labels[index]);
        }
    },
    /**
     * @private
     */
    _onClickStarBlock: function () {
        this.user_click = true;
        this.$input.val(this.get("star_value") * STAR_RATING_RATIO).change();
        this.$refresh.removeClass('d-none');
    },
    /**
     * @private
     */
    _onClickRefresh: function () {
        this.$refresh.addClass('d-none');
        this.set("star_value", 0);
        this.$input.val('').change();
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
            this.set("star_value", parseInt(this.$input.val() / STAR_RATING_RATIO));
        }
        this.user_click = false;
    },
});
return {
    RatingSelector: RatingSelector,
};
});
