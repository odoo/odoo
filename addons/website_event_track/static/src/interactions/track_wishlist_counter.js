import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";


/**
 * The following interaction is responsible for updating the wishlist counter in the header when a user adds or removes a track from their wishlist.
 * It listens for the "WEBSITE_EVENT_TRACK:ADD_ONE_TO_WISHLIST" event and updates the counter accordingly.
 * The counter is displayed in the header and shows the number of favorite tracks in their wishlist.
 * The counter is hidden when the count is zero and shown when the count is greater than zero.
 */
export class CounterWishlistInteraction extends Interaction {
    static selector = "#event_wishlist_counter";

    start() {
        this.addListener(this.env.bus, "WEBSITE_EVENT_TRACK:ADD_ONE_TO_WISHLIST", this.onReminderToggled);
        this.counter = this.el.querySelector(".track_count");
    }

    onReminderToggled(ev) {
        this.count = parseInt(this.counter.textContent, 10);
        this.count += ev.detail.reminderOn ? 1 : -1;
        if (this.count < 0) {
            this.count = 0;
        }
        this.updateBadge();
    }

    updateBadge() {
        this.counter.textContent = this.count;
        this.el.classList.toggle("d-none", this.count === 0);
    }

};

registry.category("public.interactions").add(
    "website_event_exhibitor.track_wishlist_counter",
    CounterWishlistInteraction
);
