import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";
import { PortalComposer } from "@portal/interactions/portal_composer";

/**
 * PortalComposer
 *
 * Extends Portal Composer to handle rating submission
 */
patch(PortalComposer, {
    /**
     * @override static
     */
    prepareOptions(options) {
        options = super.prepareOptions(options);
        // apply ratio to default rating value
        if (options.default_rating_value) {
            options.default_rating_value = parseFloat(options.default_rating_value);
        }
        if (options.rating_count) {
            options.rating_count = parseInt(options.rating_count);
        }

        // default options
        return Object.assign({
            "rate_with_void_content": false,
            "default_message": false,
            "default_message_id": false,
            "default_rating_value": 4.0,
            "force_submit_url": false,
            "reloadRatingPopupComposer": (data) => { },
        }, options);
    },
});

patch(PortalComposer.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            ".o-mail-Composer-stars i": {
                "t-on-click.withTarget": this.onClickStar.bind(this),
                "t-on-mousemove.withTarget": this.onMoveStar.bind(this),
                "t-on-mouseleave": this.onMoveLeaveStar.bind(this),
                "t-att-class": (el) => {
                    const index = Math.floor(this.starValue);
                    const decimal = this.starValue - index;
                    const starIndex = [...el.parentElement.children].indexOf(el) + 1; // index counts from 1 to 5
                    return {
                        "fa-star-o": starIndex > index,
                        "fa-star-half-o": decimal && starIndex === index,
                        "fa-star": decimal ? starIndex < index : starIndex <= index,
                    };
                },
            },
        });

        this.userClick = false; // user has click or not
        this.starValue = this.options.default_rating_value;
        // rating stars
        this.starListEls = this.el.querySelectorAll(".o-mail-Composer-stars i");
    },

    /**
     * @override
     */
    start() {
        super.start();
        // if this is the first review, we do not use grey color contrast, even with default rating value.
        if (!this.options.default_message_id) {
            for (const starEl of this.starListEls) {
                starEl.classList.remove("text-black-25");
            }
        }

        // set the default value to trigger the display of star widget and update the hidden input value.
        this.starValue = this.options.default_rating_value;
        this.ratingInputEl.value = this.options.default_rating_value;
    },

    get ratingInputEl() {
        return this.el.querySelector('input[name="rating_value"]');
    },

    /**
     * @override
     */
    prepareMessageData() {
        if (this.options.force_submit_url === "/mail/message/update_content") {
            return {
                attachment_ids: this.attachments.map((a) => a.id),
                attachment_tokens: this.attachments.map((a) => a.access_token),
                body: this.el.querySelector('textarea[name="message"]').value,
                hash: this.options.hash,
                message_id: parseInt(this.options.default_message_id),
                pid: this.options.pid,
                rating_value: this.ratingInputEl.value,
                token: this.options.token,
            };
        }
        const res = super.prepareMessageData(...arguments)
        res.message_id = this.options.default_message_id;
        res.post_data.rating_value = this.ratingInputEl.value;
        return res;
    },

    onClickStar(ev, oldFn, currentTargetEl) {
        const index = [...currentTargetEl.parentElement.children].indexOf(currentTargetEl);
        this.starValue = index + 1;
        this.userClick = true;
        this.ratingInputEl.value = this.starValue;
    },

    onMoveStar(ev, oldFn, currentTargetEl) {
        const index = [...currentTargetEl.parentElement.children].indexOf(currentTargetEl);
        this.starValue = index + 1;
    },

    onMoveLeaveStar() {
        if (!this.userClick) {
            this.starValue = parseInt(this.ratingInputEl.value);
        }
        this.userClick = false;
    },

    /**
     * @override
     */
    async onSubmitButtonClick(ev) {
        const result = await super.onSubmitButtonClick(...arguments);
        const modalEl = this.el.closest("#ratingpopupcomposer");
        this.addListener(modalEl, "hidden.bs.modal.noUpdate", () => {
            this.options.reloadRatingPopupComposer(result);
        });
        window.Modal.getOrCreateInstance(modalEl).hide();
    },

    /**
     * @override
     */
    onSubmitCheckContent(ev) {
        if (this.options.rate_with_void_content) {
            // TODO verify comparison
            if (this.ratingInputEl.value === "0") {
                return _t("The rating is required. Please make sure to select one before sending your review.")
            }
            return false;
        }
        return super.onSubmitCheckContent(...arguments);
    },
});
