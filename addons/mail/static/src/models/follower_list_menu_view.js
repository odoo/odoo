/** @odoo-module **/

import { attr, many, one, Model } from "@mail/model";

Model({
    name: "FollowerListMenuView",
    template: "mail.FollowerListMenuView",
    lifecycleHooks: {
        _created() {
            document.addEventListener("click", this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener("click", this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        hide() {
            this.update({ isDropdownOpen: false });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickAddFollowers(ev) {
            ev.preventDefault();
            this.hide();
            this.chatterOwner.promptAddPartnerFollower();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFollowersButton(ev) {
            this.update({ isDropdownOpen: !this.isDropdownOpen });
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydown(ev) {
            ev.stopPropagation();
            switch (ev.key) {
                case "Escape":
                    ev.preventDefault();
                    this.hide();
                    break;
            }
        },
        /**
         * Close the dropdown when clicking outside of it.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.exists()) {
                return;
            }
            // since dropdown is conditionally shown based on state, dropdownRef can be null
            if (
                this.dropdownRef &&
                this.dropdownRef.el &&
                !this.dropdownRef.el.contains(ev.target)
            ) {
                this.hide();
            }
        },
    },
    fields: {
        chatterOwner: one("Chatter", { identifying: true, inverse: "followerListMenuView" }),
        dropdownRef: attr({ ref: "dropdown" }),
        followerViews: many("FollowerView", {
            inverse: "followerListMenuViewOwner",
            compute() {
                return this.chatterOwner.thread.followers.map((follower) => ({ follower }));
            },
        }),
        isDisabled: attr({
            compute() {
                return !this.chatterOwner.hasReadAccess;
            },
        }),
        isDropdownOpen: attr({ default: false }),
    },
});
