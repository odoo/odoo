import { Composer } from "@mail/core/common/composer";

/**
 * This Component is an extension of the classic Composer used inside the chatter. It is called when a
 * user is just creating a new comment => when we set the id of the Thread to 0.
 * This enables us to limit the creation of void comments inside the DB and lessen journal entries in
 * it.
 * After comment creation, this component is destroyed and is replaced with the regular Composer.
 */

export class SpreadsheetCommentComposer extends Composer {
    constructor(...args) {
        super(...args);
    }
    /**
     * @override
     */
    async _sendMessage(value, postData) {
        await this.props.onPostCallback(value, postData);
        this.props.composer.clear();
        return;
    }
}
