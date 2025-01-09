import { models } from "@web/../tests/web_test_helpers";

export class ResUsersSettingsVolumes extends models.ServerModel {
    _name = "res.users.settings.volumes";

    /** @param {number[]} ids */
    discuss_users_settings_volume_format(ids) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        return this.browse(ids).map((volumeSettingsRecord) => {
            const [relatedGuest] = MailGuest.browse(volumeSettingsRecord.guest_id);
            const [relatedPartner] = ResPartner.browse(volumeSettingsRecord.partner_id);
            return {
                persona: {
                    id: relatedPartner ? relatedPartner.id : relatedGuest.id,
                    name: relatedPartner ? relatedPartner.name : relatedGuest.name,
                    type: relatedPartner ? "partner" : "guest",
                },
                id: volumeSettingsRecord.id,
                volume: volumeSettingsRecord.volume,
            };
        });
    }
}
