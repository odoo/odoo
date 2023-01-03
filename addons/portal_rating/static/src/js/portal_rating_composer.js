odoo.define('portal.rating.composer', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const session = require('web.session');
const portalComposer = require('portal.composer');
const {_t, qweb} = require('web.core');

const PortalComposer = portalComposer.PortalComposer;

/**
 * RatingPopupComposer
 *
 * Display the rating average with a static star widget, and open
 * a popup with the portal composer when clicking on it.
 **/
const RatingPopupComposer = publicWidget.Widget.extend({
    selector: '.o_rating_popup_composer',
    custom_events: {
        reload_rating_popup_composer: '_onReloadRatingPopupComposer',
    },

    willStart: function (parent) {
        const def = this._super.apply(this, arguments);

        const options = this.$el.data();
        this.rating_avg = Math.round(options['rating_avg'] * 100) / 100 || 0.0;
        this.rating_count = options['rating_count'] || 0.0;

        this.options = _.defaults({}, options, {
            'token': false,
            'res_model': false,
            'res_id': false,
            'pid': 0,
            'display_rating': true,
            'csrf_token': odoo.csrf_token,
            'user_id': session.user_id,
        });

        return def;
    },

    /**
     * @override
     */
    start: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._reloadRatingPopupComposer(),
        ]);
    },

    /**
     * Destroy existing ratingPopup and insert new ratingPopup widget
     *
     * @private
     * @param {Object} data
     */
    _reloadRatingPopupComposer: function () {
        if (this.options.hide_rating_avg) {
            this.$('.o_rating_popup_composer_stars').empty();
        } else {
            const ratingAverage = qweb.render(
                'portal_rating.rating_stars_static', {
                inline_mode: true,
                widget: this,
                val: this.rating_avg,
            });
            this.$('.o_rating_popup_composer_stars').empty().html(ratingAverage);
        }

        // Append the modal
        const modal = qweb.render(
            'portal_rating.PopupComposer', {
            inline_mode: true,
            widget: this,
            val: this.rating_avg,
        });
        this.$('.o_rating_popup_composer_modal').html(modal);

        if (this._composer) {
            this._composer.destroy();
        }

        // Instantiate the "Portal Composer" widget and insert it into the modal
        this._composer = new PortalComposer(this, this.options);
        return this._composer.appendTo(this.$('.o_rating_popup_composer_modal .o_portal_chatter_composer')).then(() => {
            // Change the text of the button
            this.$('.o_rating_popup_composer_text').text(
                this.options.is_fullscreen ?
                _t('Review') : this.options.default_message_id ?
                _t('Edit Review') : _t('Add Review')
            );
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onReloadRatingPopupComposer: function (event) {
        const data = event.data;

        // Refresh the internal state of the widget
        this.rating_avg = data.rating_avg;
        this.rating_count = data.rating_count;
        this.rating_value = data.rating_value;

        // Clean the dictionary
        delete data.rating_avg;
        delete data.rating_count;
        delete data.rating_value;

        this.options = _.extend(this.options, data);

        this._reloadRatingPopupComposer();
    }
});

publicWidget.registry.RatingPopupComposer = RatingPopupComposer;

return RatingPopupComposer;

});
