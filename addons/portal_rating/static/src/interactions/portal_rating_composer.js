import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { PortalComposer } from "@portal/interactions/portal_composer";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

/**
 * RatingPopupComposer
 *
 * Display the rating average with a static star widget, and open
 * a popup with the portal composer when clicking on it.
 **/
export class RatingPopupComposer extends Interaction {
    static selector = ".o_rating_popup_composer";

    setup() {
        const options = this.el.dataset;
        this.rating_avg = Math.round(options["rating_avg"] * 100) / 100 || 0.0;
        this.rating_count = options["rating_count"] || 0.0;

        this.options = Object.assign({
            "token": false,
            "res_model": false,
            "res_id": false,
            "pid": 0,
            "display_rating": true,
            "csrf_token": odoo.csrf_token,
            "user_id": user.userId,
            "reloadRatingPopupComposer": this.onReloadRatingPopupComposer.bind(this),
        }, options, {});
        this.env.bus.addEventListener("reload_rating_popup_composer", (ev) =>
            this.onReloadRatingPopupComposer(ev.detail)
        );
    }

    start() {
        this.reloadRatingPopupComposer();
    }

    /**
     * Destroy existing ratingPopup and insert new ratingPopup widget
     */
    reloadRatingPopupComposer() {
        const starsEl = this.el.querySelector(".o_rating_popup_composer_stars");
        if (this.options.hide_rating_avg) {
            starsEl.replaceChildren();
        } else {
            starsEl.replaceChildren();
            this.renderAt(
                "portal_rating.rating_stars_static", {
                inline_mode: true,
                widget: this,
                val: this.rating_avg,
            }, starsEl);
        }

        // Append the modal
        const modalEl = this.el.querySelector(".o_rating_popup_composer_modal");
        modalEl.replaceChildren();
        this.renderAt(
            "portal_rating.PopupComposer", {
            inline_mode: true,
            widget: this,
            val: this.rating_avg,
        }, modalEl);

        if (this.composerEl) {
            this.services["public.interactions"].stopInteractions(this.composerEl);
        }

        // Instantiate the "Portal Composer" widget and insert it into the modal
        // TODO Exchange options through another mean ?
        const options = PortalComposer.prepareOptions(this.options);
        // Change the text of send button
        options.send_button_label = options.default_message_id ? _t("Update review") : _t("Post review");
        this.env.portalComposerOptions = options;
        const locationEl = this.el.querySelector(".o_rating_popup_composer_modal .o_portal_chatter_composer");
        // TODO maybe always put in this.options - and prepare in setup ???
        if (!locationEl) {
            return;
        }
        this.composerEl = this.renderAt("portal.Composer", { widget: {options: this.env.portalComposerOptions }}, locationEl, "afterend")[0];
        delete this.env.portalComposerOptions;
        locationEl.remove();
        // Change the text of the button
        this.el.querySelector(".o_rating_popup_composer_text").textContent =
            options.is_fullscreen
                ? _t("Review")
                : options.default_message_id
                    ? _t("Edit Review")
                    : _t("Add Review");
    }

    /**
     * @param {OdooEvent|Object} eventOrData
     */
    onReloadRatingPopupComposer(eventOrData) {
        const data = eventOrData.data || eventOrData;
        // Refresh the internal state of the widget
        this.rating_avg = data.rating_avg || data["mail.thread"][0].rating_avg;
        this.rating_count = data.rating_count || data["mail.thread"][0].rating_count;
        this.rating_value = data.rating_value || data["rating.rating"]?.[0].rating;

        // Clean the dictionary
        delete data.rating_avg;
        delete data.rating_count;
        delete data.rating_value;

        this.updateOptions(data);
        this.reloadRatingPopupComposer();
    }

    /**
     * @param {Object} data
     */
    updateOptions(data) {
        const message = data["mail.message"] && data["mail.message"][0];
        const defaultOptions = {
            default_message:
                data.default_message || (message && message.body[1].replace(/<[^>]+>/g, "")),
            default_message_id:
                data.default_message_id ||
                (message &&
                    (message.body[1].replace(/<[^>]+>/g, "") ||
                        message.attachment_ids.length ||
                        message.rating_id) &&
                    message.id),
            default_attachment_ids: data.default_attachment_ids || data["ir.attachment"],
            default_rating_value:
                data.default_rating_value || this.rating_value || 4,
        };
        Object.assign(data, defaultOptions);
        this.options = Object.assign(this.options, data);
    }
}


registry
    .category("public.interactions")
    .add("portal_rating.rating_popup_composer", RatingPopupComposer);
