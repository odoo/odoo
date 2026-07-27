import { fields, Record } from "@mail/model/export";

/**
 * Holds the follower list state owned by a single FollowerList component.
 *
 * Each view owns its loaded followers so independently rendered lists can
 * paginate without mutating shared state on the `mail.thread` record.
 */
export class FollowerListView extends Record {
    followers = fields.Many("mail.followers");
    /** @type {string} */
    id;
    thread = fields.One("mail.thread");
}

FollowerListView.register();
