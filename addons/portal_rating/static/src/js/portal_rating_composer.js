/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import portalComposer from "@portal/js/portal_composer";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { user } from "@web/core/user";
import { Component } from "@odoo/owl";

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

        this.options = Object.assign({
            'token': false,
            'res_model': false,
            'res_id': false,
            'pid': 0,
            'display_rating': true,
            'csrf_token': odoo.csrf_token,
            'user_id': user.userId,
        }, options, {});
        Component.env.bus.addEventListener("reload_rating_popup_composer", (ev) =>
            this._onReloadRatingPopupComposer(ev.detail)
        );

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
            const ratingAverage = renderToElement(
                'portal_rating.rating_stars_static', {
                inline_mode: true,
                widget: this,
                val: this.rating_avg,
            });
            this.$('.o_rating_popup_composer_stars').empty().html(ratingAverage);
        }

        // Append the modal
        const modal = renderToElement(
            'portal_rating.PopupComposer', {
            inline_mode: true,
            widget: this,
            val: this.rating_avg,
        }) || '';
        this.$('.o_rating_popup_composer_modal').html(modal);

        if (this._composer) {
            this._composer.destroy();
        }

        // Change the text of send button
        this.options.send_button_label = this.options.default_message_id ? _t("Update review") : _t("Post review");
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
     * @param {OdooEvent|Object} eventOrData
     */
    _onReloadRatingPopupComposer: function (eventOrData) {
        const data = eventOrData.data || eventOrData;

        // Refresh the internal state of the widget
        this.rating_avg = data.rating_avg || data["mail.thread"][0].rating_avg;
        this.rating_count = data.rating_count || data["mail.thread"][0].rating_count;
        this.rating_value = data.rating_value || data["rating.rating"]?.[0].rating;

        // Clean the dictionary
        delete data.rating_avg;
        delete data.rating_count;
        delete data.rating_value;

        this._update_options(data);
        this._reloadRatingPopupComposer();
    },

    /**
     * Update the widget options using data received from the mail composer or popup rating composer
     *
     * @param {Object} data
     * @private
     */
    _update_options: function (data) {
        const message = data["mail.message"] && data["mail.message"][0];
        const updatedOptions = {
            default_message:
                data.default_message || (message && message.body.replace(/<[^>]+>/g, "")),
            default_message_id:
                data.default_message_id ||
                (message &&
                    (message.body.replace(/<[^>]+>/g, "") ||
                        message.attachment_ids.length ||
                        message.rating_id) &&
                    message.id),
            default_attachment_ids: data.default_attachment_ids || data["ir.attachment"],
            default_rating_value:
                data.default_rating_value || this.rating_value || 4,
        };
        if (message?.author && message.author.id === this.options.partner_id) {
            Object.assign(this.options, data, updatedOptions);
        }
    },
});

publicWidget.registry.RatingPopupComposer = RatingPopupComposer;

export default RatingPopupComposer;
