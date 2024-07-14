/** @odoo-module **/

import { Message } from "@mail/core/common/message";
import "@mail/core/web/message_patch"; // dependency ordering

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    /**
     * This function overrides the original method so that when the user tries to open a the record
     * from a starred discussion linked to a knowledge thread, it can be redirected to the corresponding
     * article. This is needed to avoid the user being redirected to the technical view of the
     * knowledge.article.thread model.
     * @override
     */
    async openRecord() {
        if (this.message.model === 'knowledge.article.thread') {
            const [articleThread] = await this.threadService.orm.searchRead(
                'knowledge.article.thread',
                [['id', '=', this.message.originThread.id]],
                ['article_id']
            );
            this.action.doAction({
                type: "ir.actions.act_window",
                res_id: articleThread.article_id[0],
                res_model: 'knowledge.article',
                views: [[false, "form"]],
            });
            return;
        }
        super.openRecord();
    },
});
