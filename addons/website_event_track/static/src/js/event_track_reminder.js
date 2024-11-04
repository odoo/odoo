import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { session } from "@web/session";
import { user } from "@web/core/user";

publicWidget.registry.websiteEventTrackReminder = publicWidget.Widget.extend({
    selector: ".o_wetrack_js_reminder",
    events: {
        "click .o_wetrack_js_reminder_bell": "_onReminderToggleClick",
        "click .o_form_button_cancel": "_modalEmailReminderRemove",
        "submit #o_wetrack_email_reminder_form": "_modalEmailReminderSubmit",
        "mouseover i": "_onMouseEventUpdateIcon",
        "mouseout i": "_onMouseEventUpdateIcon",
    },

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onReminderToggleClick = debounce(this._onReminderToggleClick, 500, true);
        this.notification = this.bindService("notification");
        this.orm = this.bindService("orm");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onReminderToggleClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var trackLink = ev.target;

        this.opacityManagerElement = this.el.closest(".o_we_agenda_card") ?? this.el;
        this.initialOpacity = this._getInitialOpacity();

        if (this.reminderOn === undefined) {
            this.reminderOn = trackLink.dataset.reminderOn;
        }

        var reminderOnValue = !this.reminderOn;

        var trackId = parseInt(trackLink.dataset.trackId);

        if (reminderOnValue) {
            this._checkEmailReminder(trackId);
        }
        else {
            this._removeReminder(trackId);
        }
    },

    _addReminder: function (trackId) {
        rpc("/event/track/toggle_reminder", {
            track_id: trackId,
            set_reminder_on: true,
        }).then((result) => {
            this.reminderOn = true;
            this._updateDisplay();
            Component.env.bus.trigger("open_notification_request", [
                "add_track_to_favorite",
                {
                    title: _t("Allow push notifications?"),
                    body: _t("You have to enable push notifications to get reminders for your favorite tracks."),
                    delay: 0,
                },
            ]);
        });
    },

    _getInitialOpacity: function (){
        return window.getComputedStyle(this.opacityManagerElement).getPropertyValue("opacity");
    },

    _removeReminder: function (trackId) {
        rpc("/event/track/toggle_reminder", {
            track_id: trackId,
            set_reminder_on: false,
        }).then((result) => {
            this.reminderOn = false;
            this._updateDisplay();
            this.notification.add(_t("Talk removed from your Favorites"), {
                type: "info",
            });
        });
    },

    _sendEmailReminder: async function (trackId, emailTo) {
         await rpc("/event/send_email_reminder", {
            track_id: trackId,
            email_to: emailTo
        }).then(async (result) => {
            if (result.success || result.error == "missing_template"){
                await this._addReminder(trackId);
                const favoritesInfo = _t("Track successfully added to your favorites.");
                const emailSentInfo = result.error != "missing_template" ? _t("Check your email to add them to your agenda.") : "";
                this.notification.add(
                    `${favoritesInfo} ${emailSentInfo}`,
                    {
                        type: "info",
                        className: "o_send_email_reminder_success"
                });
            }
            else {
                this.notification.add(result.message, {type: "danger", title: _t("Error")});
            }
        });
    },

    _modalEmailReminderRemove: function () {
        this.el.querySelector(".o_wetrack_js_modal_email_reminder").remove();
        this.opacityManagerElement.style.opacity = this.initialOpacity;
    },

    _isEmailReminderFormValid: function (data) {
        return data.track_id && !isNaN(data.track_id) && data.email.match(/.+@.+\..*/);
    },

    _modalEmailReminderSubmit: function (ev) {
        ev.preventDefault();
        var data = Object.fromEntries(new FormData(ev.target).entries());
        if (this._isEmailReminderFormValid(data)) {
            sessionStorage.setItem("website_event_track.email_reminder", data.email);
            this._sendEmailReminder(parseInt(data.track_id), data.email);
        }
        else {
            this.notification.add(_t("Invalid data"), {type: "danger", title: _t("Error")});
        }
        this._modalEmailReminderRemove();
    },

    _checkEmailReminder: async function (trackId){
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
            this._sendEmailReminder(trackId, emailReminder);
        }
        else {
            this.opacityManagerElement.style.opacity = 1;
            this.el.append(renderToElement("website_event_track.email_reminder_modal", {"track_id": trackId}));
        }
    },

    _updateDisplay: function () {
        var trackLink = this.el.querySelector("i");
        if (this.reminderOn) {
            trackLink.classList.replace("fa-bell-o", "fa-bell");
            trackLink.setAttribute("title", _t("Favorite On"));
        } else {
            trackLink.classList.replace("fa-bell", "fa-bell-o");
            trackLink.setAttribute("title", _t("Set Favorite"));
        }
    },

   _onMouseEventUpdateIcon: function (ev) {
        const el = ev.target;
        if (el.getAttribute("title") == _t("Set Favorite")){
            if (ev.type == "mouseover") {
                el.classList.replace("fa-bell-o", "fa-bell");
            }
            else if (ev.type == "mouseout") {
                el.classList.replace("fa-bell", "fa-bell-o");
            }
        }
    },

});

export default publicWidget.registry.websiteEventTrackReminder;
