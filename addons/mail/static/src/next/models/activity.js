import { Model } from "@web/next/store/model";
import { mailActivityFields } from "./activity_fields.generated";

/** @import { User } from "@web/next/models/user" */

/** @extends {Model<typeof mailActivityFields>} */
export class Activity extends Model {
    static _name = "mail.activity";
    static fields = mailActivityFields;

    get isOverdue() {
        return this.state() === "overdue";
    }

    get assigneeName() {
        return this.user_id()?.displayName || "";
    }

    /**
     * @param {User} user
     */
    isAssignedTo(user) {
        return this.user_id() === user;
    }

    /**
     * @param {User} user
     */
    assignTo(user) {
        if (!user.isInternal) {
            throw new Error(`${user.displayName} cannot be assigned an activity`);
        }
        this.user_id.set(user);
    }
}
