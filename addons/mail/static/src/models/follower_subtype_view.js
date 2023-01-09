/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "FollowerSubtypeView",
    template: "mail.FollowerSubtypeView",
    recordMethods: {
        /**
         * Called when clicking on cancel button.
         *
         * @param {Event} ev
         */
        onChangeCheckbox(ev) {
            if (ev.target.checked) {
                this.follower.selectSubtype(this.subtype);
            } else {
                this.follower.unselectSubtype(this.subtype);
            }
        },
    },
    fields: {
        follower: one("Follower", { related: "followerSubtypeListOwner.follower" }),
        followerSubtypeListOwner: one("FollowerSubtypeList", {
            identifying: true,
            inverse: "followerSubtypeViews",
        }),
        subtype: one("FollowerSubtype", { identifying: true, inverse: "followerSubtypeViews" }),
    },
});
