import { onWillStart } from "@odoo/owl";

import { RelationalModel } from "@web/model/relational_model/relational_model";
import { Record } from "@web/model/relational_model/record";

class CalendarFormRecord extends Record {
    async setLocation() {
        return this.update(await this._getDiscussLocationChanges());
    }

    async clearLocation() {
        // no video call is wanted here: adding an attendee must not bring the link back
        this.discussLocationCleared = true;
        return this.update({
            videocall_location: false,
            videocall_source: "custom",
        });
    }

    /**
     * Whether the meeting is owed a Discuss video call link: it has a second attendee,
     * and no link the organizer asked for or removed on purpose.
     */
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

export class CalendarFormModel extends RelationalModel {
    static Record = CalendarFormRecord;
    static withCache = false;

    setup() {
        super.setup(...arguments);
        // prefetched, so that adding the link is instant
        onWillStart(() => this.fetchDiscussVideocallLocation());
    }

    /**
     * The link of the meeting being edited, fetched once: it has a single one, whether the
     * organizer asks for it or it is offered to them.
     *
     * @returns {Promise<string>}
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
     * document, and then gets no `partner_ids` change to react to. Only a new meeting:
     * an existing one keeps what its organizer settled on.
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
