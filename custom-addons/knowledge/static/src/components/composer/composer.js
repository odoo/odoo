/** @odoo-module **/

import { Composer } from '@mail/core/common/composer';
import { useService } from '@web/core/utils/hooks';

/**
 * This Component is an extension of the classic Composer used inside the chatter. It is called when a
 * user is just creating a new comment => when we set the id of the Thread to 0.
 * This enables us to limit the creation of void comments inside the DB and lessen journal entries in
 * it.
 * After comment creation, this component is destroyed and is replaced with the regular Composer.
 */
export class KnowledgeCommentCreatorComposer extends Composer {

    setup() {
        this.orm = useService('orm');
        super.setup(...arguments);
    }
    /**
     * @override
     */
    async _sendMessage(value, postData) {
        await this.props.onPostCallback(value, postData);
        this.threadService.clearComposer(this.props.composer);
        return;
    }
}
