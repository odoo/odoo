import { models } from "@web/../tests/web_test_helpers";

export class ResUsersSettingsVolumes extends models.ServerModel {
    _name = "res.users.settings.volumes";

    /** @param {number[]} ids */
    discuss_users_settings_volume_format(ids) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        return this._filter([["id", "in", ids]]).map((volumeSettingsRecord) => {
            const [relatedGuest] = MailGuest._filter([["id", "=", volumeSettingsRecord.guest_id]]);
            const [relatedPartner] = ResPartner._filter([
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
    }
}
