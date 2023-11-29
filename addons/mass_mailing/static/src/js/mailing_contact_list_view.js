/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { MailingContactListRenderer } from "./mailing_contact_list_renderer";

export const mailingContactListView = {
    ...listView,
    Renderer: MailingContactListRenderer,
};

registry.category("views").add("mailing_contact_list", mailingContactListView);
