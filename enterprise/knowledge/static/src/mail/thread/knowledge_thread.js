import { KnowledgeMessage } from "@knowledge/mail/message/knowledge_message";
import { Thread } from "@mail/core/common/thread";
import { onMounted } from "@odoo/owl";

export class KnowledgeThread extends Thread {
    static components = { ...Thread.components, Message: KnowledgeMessage };

    setup() {
        super.setup();
        this.props.thread.knowledgePreLoading = true;
        onMounted(() => {
            this.props.thread.knowledgePreLoading = false;
        });
    }
}
