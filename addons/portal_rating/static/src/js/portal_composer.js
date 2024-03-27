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
        'click .stars i': '_onClickStar',
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
            self.input = self.el.querySelector('input[name="rating_value"]');
            self.star_list = self.el.querySelectorAll(".stars i");
            // if this is the first review, we do not use grey color contrast, even with default rating value.
            if (!self.options.default_message_id) {
                self.star_list.forEach((star) => star.classList.remove("text-black-25"));
            }

            // set the default value to trigger the display of star widget and update the hidden input value.
            self._updateStarValue(self.options.default_rating_value);
            if (self.input) {
                self.input.value = self.options.default_rating_value;
            }
        });
    },

    destroy() {
        const modalEl = this.el.closest("#ratingpopupcomposer");
        if (modalEl) {
            modalEl.removeEventListener("hidden.bs.modal", this.hideModal);
        }
        this._super(...arguments);
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
            post_data: { ...options.post_data, rating_value: this.input?.value || "" },
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
        this.star_list.forEach((star) => {
            star.classList.remove("fa-star", "fa-star-half-o");
            star.classList.add("fa-star-o");
        });

        Array.from(this.el.querySelectorAll(".stars i"))
            .slice(0, index)
            .forEach((star) => {
                star.classList.remove("fa-star-o", "fa-star-half-o");
                star.classList.add("fa-star");
            });
        if (decimal) {
            const startAtIndexEl = this.el.querySelectorAll(".stars i")[index];
            startAtIndexEl.classList.remove("fa-star-o", "fa-star", "fa-star-half-o");
            startAtIndexEl.classList.add("fa-star-half-o");
        }
    },
    /**
     * @private
     */
    _onClickStar: function (ev) {
        const starElements = this.el.querySelectorAll(".stars i");
        const index = [...starElements].indexOf(ev.currentTarget);
        this._updateStarValue(index + 1);
        this.user_click = true;
        this.input.value = this.get("star_value");
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMoveStar: function (ev) {
        const starElements = this.el.querySelectorAll(".stars i");
        const index = [...starElements].indexOf(ev.currentTarget);
        this._updateStarValue(index + 1);
    },
    /**
     * @private
     */
    _onMoveLeaveStar: function () {
        if (!this.user_click) {
            this._updateStarValue(parseInt(this.input.value));
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
                const modalEl = this.el.closest("#ratingpopupcomposer");
                if (modalEl) {
                    this.hideModal = () => {
                        this.trigger_up("reload_rating_popup_composer", result);
                    };
                    modalEl.addEventListener("hidden.bs.modal", this.hideModal);
                    const modal = Modal.getOrCreateInstance(modalEl);
                    modal.hide();
                }
            },
            () => {}
        );
    },

    /**
     * @override
     * @private
     */
    _onSubmitCheckContent: function (ev) {
        if (this.options.rate_with_void_content) {
            if (this.input.value === 0) {
                return _t('The rating is required. Please make sure to select one before sending your review.')
            }
            return false;
        }
        return this._super.apply(this, arguments);
    },
});
