import RatingPopupComposer from "@portal_rating/js/portal_rating_composer";

RatingPopupComposer.include({
    _update_options: function (data) {
        this._super(...arguments);
        this.options.force_submit_url =
            data.force_submit_url ||
            (this.options.default_message_id && "/slides/mail/update_comment");
    },
});
