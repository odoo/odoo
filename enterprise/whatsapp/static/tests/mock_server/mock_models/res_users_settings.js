import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class ResUsersSettings extends mailModels.ResUsersSettings {
    is_discuss_sidebar_category_whatsapp_open = fields.Boolean({ default: true });
}
