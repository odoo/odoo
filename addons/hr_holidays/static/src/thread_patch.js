import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get showOutOfOfficeAlert() {
        return this.props.thread.model === 'discuss.channel' && this.props.thread.correspondent?.persona.outOfOfficeDateEndText;
    },
});
