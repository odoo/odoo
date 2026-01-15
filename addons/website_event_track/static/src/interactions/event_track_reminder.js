import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { isEmail } from "@web/core/utils/strings";

export class WebsiteEventTrackReminder extends Interaction {
    static selector = ".o_wetrack_js_reminder";

    dynamicContent = {
        ".o_wetrack_js_reminder_bell": {
            "t-on-click.prevent.stop": this.debounced(this.onReminderToggleClick, 500, true),
            "t-on-mouseover.withTarget": (ev, targetEl) => {
                if (!this.reminderOn){
                    targetEl.classList.replace("fa-bell-o", "fa-bell");
                }
            },
            "t-on-mouseout.withTarget": (ev, targetEl) => {
                if (!this.reminderOn){
                    targetEl.classList.replace("fa-bell", "fa-bell-o");
                }
            },
        },
        ".o_form_button_cancel": {
            "t-on-click": this.modalEmailReminderCancel,
        },
        "#o_wetrack_email_reminder_form": {
            "t-on-submit.prevent": this.modalEmailReminderSubmit,
        },
        ".o_form_button_dont_ask_again": {
            "t-on-click": () => {
                sessionStorage.setItem("website_event_track.email_reminder_off", "true");
                this.modalEmailReminderCancel();
            },
        }
    };

    setup() {
        this.notification = this.services.notification;
        this.orm = this.services.orm;
        this.trackId = parseInt(this.el.dataset.trackId);
        this.reminderOn = this.el.dataset.reminderOn;
        this.bellSelectorEl = this.el.querySelector(".o_wetrack_js_reminder_bell");
    }

    async onReminderToggleClick() {
        this.opacityManagerElement = this.el.closest(".o_we_agenda_card") ?? this.el;
        this.initialOpacity = window.getComputedStyle(this.opacityManagerElement).getPropertyValue("opacity");

        const reminderOnValue = !this.reminderOn;
        await this._toggleReminder(reminderOnValue);

        if (reminderOnValue) {
            this._checkEmailReminder();
        }
    }

    async _toggleReminder(reminderOnValue) {
        await rpc("/event/track/toggle_reminder", {
            track_id: this.trackId,
            set_reminder_on: reminderOnValue,
        }).then((result) => {
            if (result.error && result.error === "ignored") {
                this.notification.add(
                    _t("Talk already in your Favorites. The page does not seem to be up-to-date and needs a refresh."),
                    {type: "info"}
                 );
            } else {
                this.reminderOn = reminderOnValue;
                if (this.reminderOn) {
                    this.favoriteAddedConfirmation = _t("Track successfully added to your favorites.");
                    Component.env.bus.trigger("open_notification_request", [
                        "add_track_to_favorite",
                        {
                            title: _t("Allow push notifications?"),
                            body: _t("You have to enable push notifications to get reminders for your favorite tracks."),
                            delay: 0
                        },
                    ]);
                    this.bellSelectorEl.classList.replace("fa-bell-o", "fa-bell");
                    this.bellSelectorEl.setAttribute("title", _t("Favorite On"));
                } else {
                    this.notification.add(_t("Talk removed from your Favorites"), {
                        type: "info",
                    });
                    this.favoriteAddedConfirmation = "";
                    this.bellSelectorEl.classList.replace("fa-bell", "fa-bell-o");
                    this.bellSelectorEl.setAttribute("title", _t("Set Favorite"));
                }
            }
        });
    }

    async _checkEmailReminder() {
        const emailReminder = sessionStorage.getItem("website_event_track.email_reminder_email");
        if (emailReminder || !session.is_public) {
            this._sendEmailReminder(session.is_public ? emailReminder : null);
        }
        else if (!sessionStorage.getItem("website_event_track.email_reminder_off")) {
            this.opacityManagerElement.style.opacity = 1;
            this.insert(renderToElement("website_event_track.email_reminder_modal", {"track_id": this.trackId}));
        }
        else if (this.favoriteAddedConfirmation) {
            this.notification.add(this.favoriteAddedConfirmation, {type: "info"});
        }
    }

    modalEmailReminderCancel() {
        this._modalEmailReminderRemove();
        if (this.favoriteAddedConfirmation) {
            this.notification.add(this.favoriteAddedConfirmation, {type: "info"});
        }
    }

    _modalEmailReminderRemove() {
        this.el.querySelector(".o_wetrack_js_modal_email_reminder").remove();
        this.opacityManagerElement.style.opacity = this.initialOpacity;
    }

    modalEmailReminderSubmit(ev) {
        const data = Object.fromEntries(new FormData(ev.target).entries());
        if (this.favoriteAddedConfirmation) {
            this.notification.add(this.favoriteAddedConfirmation, {type: "info"});
        }
        if (data.track_id && !isNaN(data.track_id) && isEmail(data.email)) {
            sessionStorage.setItem("website_event_track.email_reminder_email", data.email);
            this._sendEmailReminder(data.email);
        }
        else if (!isEmail(data.email)) {
            this.notification.add(_t("Invalid email"), {type: "danger", title: _t("Email Error")});
        }
        else {
            this.notification.add(_t("Invalid data"), {type: "danger", title: _t("Email Error")});
        }
        this._modalEmailReminderRemove();
    }

    async _sendEmailReminder(emailTo) {
         await rpc("/event/track/send_email_reminder", {
            track_id: this.trackId,
            email_to: emailTo
        }).then(async (result) => {
            if (result.success || result.error == "missing_template"){
                const emailSentInfo = result.error != "missing_template" ? _t("Check your email to add the track to your agenda.") : "";
                this.notification.add(
                    [this.favoriteAddedConfirmation, emailSentInfo].join(" "),
                    {type: "info", className: "o_send_email_reminder_success"}
                );
            }
            else {
                if (this.favoriteAddedConfirmation) {
                    this.notification.add(this.favoriteAddedConfirmation, {type: "info"});
                }
                this.notification.add(result.message, {type: "danger", title: _t("Email Error")});
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_track_reminder", WebsiteEventTrackReminder);
