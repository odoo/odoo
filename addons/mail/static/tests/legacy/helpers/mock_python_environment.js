/** @odoo-module alias=@mail/../tests/helpers/mock_python_environment default=false */

import { pyEnvTarget } from "@bus/../tests/helpers/mock_python_environment";

import { patch } from "@web/core/utils/patch";

patch(pyEnvTarget, {
    getSelfData() {
        if (this.currentGuest) {
            return {
                id: this.currentGuest.id,
                name: this.currentGuest.name,
                type: "guest",
                write_date: this.currentGuest.write_date,
            };
        } else if (this.currentUser) {
            return {
                id: this.currentUser.partner_id,
                isAdmin: true, // mock server simplification
                isInternalUser: !this.currentUser.share,
                name: this.currentUser.name,
                notification_preference: this.currentUser.notification_type,
                type: "partner",
                userId: this.currentUser.id,
                write_date: this.currentUser.write_date,
            };
        }
    },
    getUserSettings() {
        if (!this.currentGuest && this.currentUser) {
            const userSettings = this.mockServer._mockResUsersSettings_FindOrCreateForUser(
                this.currentUser.id
            );
            const settings = this.mockServer._mockResUsersSettings_ResUsersSettingsFormat(
                userSettings.id
            );
            return settings;
        }
        return super.getUserSettings();
    },
    async withGuest(guestId, fn) {
        const [guest] = await this.mockServer.getRecords("mail.guest", [["id", "=", guestId]]);
        const originalGuest = this.cookie.get("dgid");
        if (!guest) {
            throw new Error(`Guest ${guestId} not found`);
        }
        let result;
        try {
            this.cookie.set("dgid", guestId);
            result = await this.withUser(this.publicUserId, fn);
        } finally {
            this.cookie.set("dgid", originalGuest);
        }
        return result;
    },

    get currentGuest() {
        const dgid = this.cookie.get("dgid");
        if (!dgid) {
            return undefined;
        }
        return this.mockServer.getRecords("mail.guest", [["id", "=", dgid]])[0];
    },
});
