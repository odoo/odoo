import { mailing_variable } from "../builder/plugins/customize_mailing_plugin";

declare module "plugins" {
    interface HistoryDataProperties {
        mailing_variable: mailing_variable;
    }
}
