/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { patch } from "@web/core/utils/patch";

patch(threadActionsRegistry.get("expand-form"), {
    async open(component) {
        if (component.thread.model === "knowledge.article.thread") {
            const [articleThreadData] = await component.env.services.orm.read(
                "knowledge.article.thread",
                [component.thread.id],
                ["article_id"],
                { load: false }
            );
            component.actionService.doAction("knowledge.ir_actions_server_knowledge_home_page", {
                stackPosition: "replaceCurrentAction",
                additionalContext: {
                    res_id: articleThreadData["article_id"],
                },
            });
            await component.props.chatWindow.close();
        } else {
            super.open(component);
        }
    },
});
