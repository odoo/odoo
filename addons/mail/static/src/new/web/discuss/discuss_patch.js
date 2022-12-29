/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Sidebar } from "@mail/new/web/discuss/sidebar";
import { Discuss } from "@mail/new/discuss/discuss";
import { MessagingMenu } from "@mail/new/web/messaging_menu/messaging_menu";

patch(Discuss, "mail/web", {
    components: { ...Discuss.components, Sidebar, MessagingMenu },
});
