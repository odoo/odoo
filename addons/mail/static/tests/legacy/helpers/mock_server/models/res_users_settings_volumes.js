/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/res_users_settings_volumes default=false */

// ensure bus mock server is loaded first.
import "@bus/../tests/helpers/mock_server";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `discuss_users_settings_volume_format` on `res.users.settings.volumes`.
     *
     * @param {Number[]} ids
     * @returns {Object}
     */
    _mockResUsersSettingsVolumes_DiscussUsersSettingsVolumeFormat(ids) {
        const volumeSettingsRecords = this.getRecords("res.users.settings.volumes", [
            ["id", "in", ids],
        ]);
        return volumeSettingsRecords.map((volumeSettingsRecord) => {
            const [relatedGuest] = this.getRecords("mail.guest", [
                ["id", "=", volumeSettingsRecord.guest_id],
            ]);
            const [relatedPartner] = this.getRecords("res.partner", [
                ["id", "=", volumeSettingsRecord.partner_id],
            ]);
            return {
                guest_id: relatedGuest ? { id: relatedGuest.id, name: relatedGuest.name } : false,
                id: volumeSettingsRecord.id,
                partner_id: relatedPartner
                    ? { id: relatedPartner.id, name: relatedPartner.name }
                    : false,
                volume: volumeSettingsRecord.volume,
            };
        });
    },
});
