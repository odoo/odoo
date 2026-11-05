import { MailingListSubscribeOptionPlugin } from "../website_builder/mailing_list_subscribe_option_plugin";
import { RecaptchaSubscribeOptionPlugin } from "../website_builder/recaptcha_subscribe_option_plugin";

declare module "plugins" {
    interface SharedMethods {
        mailingListSubscribeOption: SharedOf<typeof MailingListSubscribeOptionPlugin>;
        recaptchaSubscribeOption: SharedOf<typeof RecaptchaSubscribeOptionPlugin>;
    }
}
