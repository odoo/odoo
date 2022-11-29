/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Sidebar } from "@mail/web/discuss/sidebar";
import { Discuss } from "@mail/discuss/discuss";
import { MessagingMenu } from "@mail/web/messaging_menu/messaging_menu";

patch(Discuss, "mail/web", {
    components: { ...Discuss.components, Sidebar, MessagingMenu },
});
