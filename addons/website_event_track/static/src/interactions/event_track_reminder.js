import { debounce } from "@web/core/utils/timing";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { session } from "@web/session";
import { user } from "@web/core/user";

export class WebsiteEventTrackReminder extends Interaction {
    static selector = ".o_wetrack_js_reminder";
    dynamicContent = {
        ".o_wetrack_js_reminder_bell": {
            "t-on-click": this._onReminderToggleClick,
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
            "t-on-click": this._modalReminderCancel,
        },
        "#o_wetrack_email_reminder_form": {
            "t-on-submit.prevent": this._modalEmailReminderSubmit,
        },
        ".o_form_button_dont_ask_again": {
            "t-on-click": () => {
                    sessionStorage.setItem("website_event_track.dont_ask_email_reminder", "true");
                    this._modalReminderCancel();
            },
        }
    };

    setup() {
        this._onReminderToggleClick = debounce(this._onReminderToggleClick, 500, true);
        this.notification = this.services.notification;
        this.orm = this.services.orm;
        this.trackId = parseInt(this.el.dataset.trackId);
        this.reminderOn = this.el.dataset.reminderOn;
        this.reminderBell = this.el.querySelector(".o_wetrack_js_reminder_bell");
    }

    async _onReminderToggleClick() {

        this.opacityManagerElement = this.el.closest(".o_we_agenda_card") ?? this.el;
        this.initialOpacity = window.getComputedStyle(this.opacityManagerElement).getPropertyValue("opacity");

        var reminderOnValue = !this.reminderOn;

        await this._toggleReminder(reminderOnValue);

        if (reminderOnValue && sessionStorage.getItem("website_event_track.dont_send_email_reminder") != "true") {
            this._checkEmailReminder();
        }

    }

    async _toggleReminder(reminderOnValue) {
        await rpc("/event/track/toggle_reminder", {
            track_id: this.trackId,
            set_reminder_on: reminderOnValue,
        }).then((result) => {
            if (result.error && result.error === "ignored") {
                this.notification.add(_t("Talk already in your Favorites"), {
                    type: "info",
                    title: _t("Error"),
                });
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
                    this.reminderBell.classList.replace("fa-bell-o", "fa-bell");
                    this.reminderBell.setAttribute("title", _t("Favorite On"));
                } else {
                    this.notification.add(_t("Talk removed from your Favorites"), {
                        type: "info",
                    });
                    this.favoriteAddedConfirmation = "";
                    this.reminderBell.classList.replace("fa-bell", "fa-bell-o");
                    this.reminderBell.setAttribute("title", _t("Set Favorite"));
                }
            }
        });
    }

    async _sendEmailReminder(emailTo) {
         await rpc("/event/send_email_reminder", {
            track_id: this.trackId,
            email_to: emailTo
        }).then(async (result) => {
            if (result.success || result.error == "missing_template"){
                const emailSentInfo = result.error != "missing_template" ? _t("Check your email to add them to your agenda.") : "";
                this.notification.add(
                    `${this.favoriteAddedConfirmation} ${emailSentInfo}`,
                    {
                        type: "info",
                        className: "o_send_email_reminder_success"
                    }
                );
            }
            else {
                this.notification.add(result.message, {type: "danger", title: _t("Error")});
            }
        });
    }

    _modalEmailReminderRemove() {
        this.el.querySelector(".o_wetrack_js_modal_email_reminder").remove();
        this.opacityManagerElement.style.opacity = this.initialOpacity;
    }

    _modalReminderCancel() {
        this._modalEmailReminderRemove();
        if (this.favoriteAddedConfirmation) {
            this.notification.add(this.favoriteAddedConfirmation, {type: "info"});
        }
    }

    _modalEmailReminderSubmit(ev) {
        var data = Object.fromEntries(new FormData(ev.target).entries());
        if (data.track_id && !isNaN(data.track_id) && data.email.match(/.+@.+\..*/)) {
            sessionStorage.setItem("website_event_track.email_reminder", data.email);
            this._sendEmailReminder(data.email);
        }
        else {
            this.notification.add(_t("Invalid data"), {type: "danger", title: _t("Error")});
        }
        this._modalEmailReminderRemove();
    }

    async _checkEmailReminder(){
        var mustUpdateEmailReminder = sessionStorage.getItem("website_event_track.user_is_public") != session.is_public.toString();
        sessionStorage.setItem("website_event_track.user_is_public", session.is_public);

        if (!session.is_public && mustUpdateEmailReminder){
             await this.orm.read("res.users", [user.userId], ["email"]).then((u) => {
                if (u.length === 1 && u[0].email) {
                    sessionStorage.setItem("website_event_track.email_reminder", u[0].email);
                    mustUpdateEmailReminder = false;
                }
            });
        }
        var emailReminder = sessionStorage.getItem("website_event_track.email_reminder");
        if (emailReminder && !mustUpdateEmailReminder){
            this._sendEmailReminder(emailReminder);
        }
        else if (!sessionStorage.getItem("website_event_track.dont_ask_email_reminder")){
            this.opacityManagerElement.style.opacity = 1;
            this.insert(renderToElement("website_event_track.email_reminder_modal", {"track_id": this.trackId}));
        }
        else if (this.favoriteAddedConfirmation) {
            this.notification.add(this.favoriteAddedConfirmation, {type: "info"});
        }
    }

}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_track_reminder", WebsiteEventTrackReminder);
