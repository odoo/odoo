/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import portalComposer from "@portal/js/portal_composer";

var PortalComposer = portalComposer.PortalComposer;

/**
 * PortalComposer
 *
 * Extends Portal Composer to handle rating submission
 */
PortalComposer.include({
    events: Object.assign({}, PortalComposer.prototype.events, {
        'click .o-mail-Composer-stars i': '_onClickStar',
        'mousemove .o-mail-Composer-stars i': '_onMoveStar',
        'mouseleave .o-mail-Composer-stars i': '_onMoveLeaveStar',
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
        this.options = Object.assign({
            'rate_with_void_content': false,
            'default_message': false,
            'default_message_id': false,
            'default_rating_value': 4.0,
            'force_submit_url': false,
        }, this.options);
        this.user_click = false; // user has click or not
        this._starValue = this.options.default_rating_value;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // rating stars
            self.$input = self.$('input[name="rating_value"]');
            self.$star_list = self.$('.o-mail-Composer-stars').find('i');
            // if this is the first review, we do not use grey color contrast, even with default rating value.
            if (!self.options.default_message_id) {
                self.$star_list.removeClass('text-black-25');
            }

            // set the default value to trigger the display of star widget and update the hidden input value.
            self._updateStarValue(self.options.default_rating_value);
            self.$input.val(self.options.default_rating_value);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _prepareMessageData: function () {
        const options = this._super(...arguments);
        return Object.assign(options || {}, {
            message_id: this.options.default_message_id,
            post_data: { ...options.post_data, rating_value: this.$input.val() },
        });
    },
    /**
     * @private
     */
    _updateStarValue: function (val) {
        this._starValue = val;
        var index = Math.floor(val);
        var decimal = val - index;
        // reset the stars
        this.$star_list.removeClass('fa-star fa-star-half-o').addClass('fa-star-o');

        this.$('.o-mail-Composer-stars').find("i:lt(" + index + ")").removeClass('fa-star-o fa-star-half-o').addClass('fa-star');
        if (decimal) {
            this.$('.o-mail-Composer-stars').find("i:eq(" + index + ")").removeClass('fa-star-o fa-star fa-star-half-o').addClass('fa-star-half-o');
        }
    },
    /**
     * @private
     */
    _onClickStar: function (ev) {
        var index = this.$('.o-mail-Composer-stars i').index(ev.currentTarget);
        this._updateStarValue(index + 1);
        this.user_click = true;
        this.$input.val(this._starValue);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMoveStar: function (ev) {
        var index = this.$('.o-mail-Composer-stars i').index(ev.currentTarget);
        this._updateStarValue(index + 1);
    },
    /**
     * @private
     */
    _onMoveLeaveStar: function () {
        if (!this.user_click) {
            this._updateStarValue(parseInt(this.$input.val()));
        }
        this.user_click = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onSubmitButtonClick: function (ev) {
        return this._super(...arguments).then((result) => {
            const $modal = this.$el.closest('#ratingpopupcomposer');
            $modal.on('hidden.bs.modal', () => {
              this.trigger_up('reload_rating_popup_composer', result);
            });
            $modal.modal('hide');
        }, () => {});
    },

    /**
     * @override
     * @private
     */
    _onSubmitCheckContent: function (ev) {
        if (this.options.rate_with_void_content) {
            if (this.$input.val() === 0) {
                return _t('The rating is required. Please make sure to select one before sending your review.')
            }
            return false;
        }
        return this._super.apply(this, arguments);
    },
});
