/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "FollowerView",
    template: "mail.FollowerView",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickDetails(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            this.follower.openProfile();
            this.followerListMenuViewOwner.hide();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickEdit(ev) {
            ev.preventDefault();
            this.follower.showSubtypes();
            this.followerListMenuViewOwner.hide();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickRemove(ev) {
            const followerListMenuView = this.followerListMenuViewOwner;
            this.follower.remove();
            if (followerListMenuView.chatterOwner) {
                followerListMenuView.chatterOwner.reloadParentView({
                    fieldNames: ["message_follower_ids"],
                });
            }
            followerListMenuView.hide();
        },
    },
    fields: {
        follower: one("Follower", { identifying: true, inverse: "followerViews" }),
        followerListMenuViewOwner: one("FollowerListMenuView", {
            identifying: true,
            inverse: "followerViews",
        }),
    },
});
