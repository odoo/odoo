odoo.define('portal.rating.composer', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var session = require('web.session');
var portalComposer = require('portal.composer');

var PortalComposer = portalComposer.PortalComposer;

/**
 * RatingPopupComposer
 *
 * Display the rating average with a static star widget, and open
 * a popup with the portal composer when clicking on it.
 **/
var RatingPopupComposer = publicWidget.Widget.extend({
    template: 'portal_rating.PopupComposer',
    xmlDependencies: [
        '/portal/static/src/xml/portal_chatter.xml',
        '/portal_rating/static/src/xml/portal_tools.xml',
        '/portal_rating/static/src/xml/portal_rating_composer.xml',
    ],

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.rating_avg = Math.round(options['ratingAvg'] * 100) / 100 || 0.0;
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

return RatingPopupComposer;

});
