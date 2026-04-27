import { Composer } from "@mail/core/common/composer";
import { useService } from "@web/core/utils/hooks";
import { onWillDestroy } from "@odoo/owl";

/**
 * This Component is an extension of the classic Composer used inside the chatter. It is called when a
 * user is just creating a new comment => when we set the id of the Thread to undefined.
 * This enables us to limit the creation of void comments inside the DB and lessen journal entries in
 * it.
 * After comment creation, this component is destroyed and is replaced with the regular Composer.
 */
export class KnowledgeCommentCreatorComposer extends Composer {
    static props = [...Composer.props, "onCreateThreadCallback?"];

    setup() {
        super.setup();
        this.commentsService = useService("knowledge.comments");
        this.newThread = undefined;
        onWillDestroy(() => {
            this.props.onCreateThreadCallback?.(this.newThread);
        });
    }

    /**
     * @override
     */
    async _sendMessage(value, postData) {
        this.newThread = await this.commentsService.createThread(value, postData);
        this.clear();
    }
}
