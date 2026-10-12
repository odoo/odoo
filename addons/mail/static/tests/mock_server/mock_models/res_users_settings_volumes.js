import { models } from "@web/../tests/web_test_helpers";

export class ResUsersSettingsVolumes extends models.ServerModel {
    _name = "res.users.settings.volumes";

    _store_volume_fields(res) {
        res.extend(["guest_id", "partner_id", "user_setting_id", "volume"]);
    }
}
