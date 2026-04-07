import { listView } from "@web/views/list/list_view";
import { MailingListListController } from "./mass_mailing_list_list_controller";
import { registry } from "@web/core/registry";

export const MailingListListView = {
    ...listView,
    Controller: MailingListListController,
};

registry.category("views").add("mailing_list_list_view", MailingListListView);
