import { onWillStart } from "@odoo/owl";

import { RelationalModel } from "@web/model/relational_model/relational_model";
import { Record } from "@web/model/relational_model/record";

class CalendarFormRecord extends Record {

    async setLocation() {
        const videoLocation = await this.model.discussVideocallLocation;
        this.update({
            access_token: videoLocation.split("/").pop(),
            videocall_location: videoLocation,
            videocall_source: "discuss",
        });
    }

    async clearLocation() {
        this.update({
            videocall_location: false,
            videocall_source: "custom",
        });
    }
}

export class CalendarFormModel extends RelationalModel {
    static Record = CalendarFormRecord;

    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            this.discussVideocallLocation = this.orm.call(
                "calendar.event",
                "get_discuss_videocall_location"
            );
        });
    }
}
