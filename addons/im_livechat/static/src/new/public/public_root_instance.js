/** @odoo-module alias=root.widget */

import { PublicRoot, createPublicRoot } from "@web/legacy/js/public/public_root";
import { LivechatRoot } from "@im_livechat/new/core/livechat_root";
import { createRootNode, initializeLivechatContainer } from "@im_livechat/new/core/boot_helpers";
import { registry } from "@web/core/registry";
import { whenReady } from "@odoo/owl";
import { serverUrl } from "@im_livechat/livechat_data";
import { session } from "@web/session";

session.origin = serverUrl;
registry.category("main_components").remove("mail.ChatWindowContainer");

async function initializeLivechat() {
    await whenReady();
    const root = createRootNode();
    const target = await initializeLivechatContainer(root);
    registry
        .category("main_components")
        .add("im_livechat.LivechatRoot", { Component: LivechatRoot });
    return createPublicRoot(PublicRoot, { target });
}

export default initializeLivechat();
