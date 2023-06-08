/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { MessagingMenu } from "@mail/core/web/messaging_menu";
import { Sidebar } from "@mail/core/web/sidebar";

import { patch } from "@web/core/utils/patch";

patch(Discuss, "mail/core/web", {
    components: { ...Discuss.components, Sidebar, MessagingMenu },
});
