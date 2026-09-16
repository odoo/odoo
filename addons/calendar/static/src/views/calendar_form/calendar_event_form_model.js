import { onWillStart } from "@odoo/owl";

import { RelationalModel } from "@web/model/relational_model/relational_model";
import { Record } from "@web/model/relational_model/record";

class CalendarEventFormRecord extends Record {
    /** @type {boolean} the organizer removed the link: do not put one back. */
    discussLocationCleared = false;

    async setLocation() {
        return this.update(await this._getDiscussLocationChanges());
    }

    async clearLocation() {
        this.discussLocationCleared = true;
        return this.update({
            videocall_location: false,
            videocall_source: "custom",
        });
    }

    /** A meeting held with someone else is worth a video call link, unless the organizer
     * already turned one down. */
    get needsDiscussLocation() {
        return (
            !this.discussLocationCleared &&
            "videocall_location" in this.data &&
            !this.data.videocall_location &&
            this.data.partner_ids?.currentIds.length > 1
        );
    }

    async _getDiscussLocationChanges() {
        const videoLocation = await this.model.fetchDiscussVideocallLocation();
        return {
            access_token: videoLocation.split("/").pop(),
            videocall_location: videoLocation,
            videocall_source: "discuss",
        };
    }

    /**
     * Give the meeting its video call link as soon as it has a second attendee, rather
     * than waiting for the organizer to ask for one.
     *
     * @override
     */
    async _update(changes, options) {
        await super._update(changes, options);
        if ("partner_ids" in changes && this.needsDiscussLocation) {
            await super._update(await this._getDiscussLocationChanges(), {
                withoutOnchange: true,
            });
        }
    }
}

export class CalendarEventFormModel extends RelationalModel {
    static Record = CalendarEventFormRecord;
    static withCache = false;

    /** @type {Promise<string>|undefined} the pending or resolved link fetch. */
    discussVideocallLocation;

    setup() {
        super.setup(...arguments);
        onWillStart(() => {
            this.fetchDiscussVideocallLocation();
        });
    }

    /**
     * Fetch the video call link to give the meeting, and keep it for the whole form: a
     * meeting only ever gets one, so adding it is instant whenever it is needed.
     */
    fetchDiscussVideocallLocation() {
        this.discussVideocallLocation ??= this.orm.call(
            "calendar.event",
            "get_discuss_videocall_location"
        );
        return this.discussVideocallLocation;
    }

    /**
     * A meeting may open with its attendees already filled in, e.g. scheduled from a
     * document, and then gets no `partner_ids` change to react to. To solve this, give
     * it its link on load too, and only when it is new: an existing meeting keeps what
     * its organizer settled on.
     *
     * @override
     */
    async load(params) {
        await super.load(params);
        if (this.root && !this.root.resId && this.root.needsDiscussLocation) {
            await this.root.setLocation();
        }
    }
}
