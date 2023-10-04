/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { DiscussSidebar } from "@mail/core/web/discuss_sidebar";
import { MessagingMenu } from "@mail/core/web/messaging_menu";

import { ControlPanel } from "@web/search/control_panel/control_panel";

Object.assign(Discuss.components, { ControlPanel, DiscussSidebar, MessagingMenu });
