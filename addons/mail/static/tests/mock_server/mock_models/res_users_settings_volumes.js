import { models } from "@web/../tests/web_test_helpers";

export class ResUsersSettingsVolumes extends models.ServerModel {
    _name = "res.users.settings.volumes";

    _store_volume_fields(res) {
        res.extend(["volume"]);
        res.one("partner_id", "_store_avatar_fields");
        res.one("guest_id", "_store_avatar_fields");
        res.one("user_setting_id", []);
    }

    /** @param {number[]} ids */
    discuss_users_settings_volume_format(ids) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        return this.browse(ids).map((volumeSettingsRecord) => {
            const [relatedGuest] = MailGuest.browse(volumeSettingsRecord.guest_id);
            const [relatedPartner] = ResPartner.browse(volumeSettingsRecord.partner_id);
            let partner_id, guest_id;
            if (relatedPartner) {
                partner_id = {
                    id: relatedPartner.id,
                    name: relatedPartner.name,
                };
            }
            if (relatedGuest) {
                guest_id = {
                    id: relatedGuest.id,
                    name: relatedGuest.name,
                };
            }
            return {
                partner_id,
                guest_id,
                id: volumeSettingsRecord.id,
                volume: volumeSettingsRecord.volume,
            };
        });
    }
}
