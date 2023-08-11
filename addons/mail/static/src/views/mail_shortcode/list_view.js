/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { MailShortcodeListRenderer } from "./list_renderer";

export const MailShortcodeListView = {
    ...listView,
    Renderer: MailShortcodeListRenderer,
};

registry.category("views").add("mail_shortcode_list", MailShortcodeListView);
