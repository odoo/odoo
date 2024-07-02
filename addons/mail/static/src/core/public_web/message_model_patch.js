import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    _onUpdateIsEmpty() {
        super._onUpdateIsEmpty(...arguments);
        if (this.isEmpty && this.starred) {
            const starred = this.store.discuss.starred;
            starred.counter--;
            starred.messages.delete(this);
        }
    },
});
