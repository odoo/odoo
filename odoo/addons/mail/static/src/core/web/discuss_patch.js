/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { DiscussSidebar } from "@mail/core/web/discuss_sidebar";
import { MessagingMenu } from "@mail/core/web/messaging_menu";

Object.assign(Discuss.components, { DiscussSidebar, MessagingMenu });
