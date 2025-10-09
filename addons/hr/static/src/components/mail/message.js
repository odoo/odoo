import { Message } from "@mail/core/common/message";

export class HRMessage extends Message {
    static template = "hr.Message";

    setup() {
        super.setup();
        this.removeUrl = this.props.thread.model == 'hr.employee' && this.props.message.model == 'hr.version';
    }
}
