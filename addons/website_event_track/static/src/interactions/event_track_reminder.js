import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteEventTrackReminder extends Interaction {
    static selector = ".o_wetrack_js_reminder";

    dynamicContent = {
        _root: { "t-on-click.prevent.stop": this.debounced(this.onReminderToggleClick, 500, true) },
        "i" : { 
            "t-att-class": () => ({ "fa-bell": this.reminderOn, "fa-bell-o": !this.reminderOn }),
            "t-att-title": () => this.reminderOn ? _t("Favorite On") : _t("Set Favorite"),
        },
    };

    setup() {
        this.bellSelectorEl = this.el.querySelector("i");
        this.reminderOn = this.bellSelectorEl.dataset.reminderOn;
    }

    async onReminderToggleClick(ev) {
        const reminderOnValue = !this.reminderOn;

        const result = await this.waitFor(rpc("/event/track/toggle_reminder", {
            track_id: parseInt(this.bellSelectorEl.dataset.trackId),
            set_reminder_on: reminderOnValue,
        }));

        this.protectSyncAfterAsync(() => {
            if (result.error && result.error === "ignored") {
                this.services.notification.add(
                    _t("Talk already in your Favorites"),
                    {
                        type: "info",
                        title: _t("Error"),
                    }
                );
            } else {
                this.reminderOn = reminderOnValue;
                const message = this.reminderOn
                    ? _t("Talk added to your Favorites")
                    : _t("Talk removed from your Favorites");
                this.services.notification.add(message, {
                    type: "info",
                });
                if (this.reminderOn) {
                    Component.env.bus.trigger("open_notification_request", [
                        "add_track_to_favorite",
                        {
                            title: _t("Allow push notifications?"),
                            body: _t(
                                "You have to enable push notifications to get reminders for your favorite tracks."
                            ),
                            delay: 0,
                        },
                    ]);
                }
            }
        })();        
    }
}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_track_reminder", WebsiteEventTrackReminder);
