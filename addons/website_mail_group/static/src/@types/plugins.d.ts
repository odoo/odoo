import { MailGroupOptionPlugin } from "../website_builder/mail_group_option_plugin";

declare module "plugins" {
    interface SharedMethods {
        mailGroupOption: SharedOf<typeof MailGroupOptionPlugin>;
    }
}
