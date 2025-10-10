import { Thread } from "@mail/core/common/thread";

export class HRThread extends Thread {
    static props = [
        ...this.props,
        "context",
    ];

    get orderedMessages() {
        let messages = super.orderedMessages
        if (this.props.thread.model != "hr.employee")
            return messages;
        return messages.filter(message => message.model != "hr.version" || message.res_id == this.props.context.version_id)
    }
}
