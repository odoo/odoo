import { patch } from "@web/core/utils/patch";

import { Thread } from '@mail/core/common/thread';

patch(Thread.prototype, {
    get displayMessages() {
        let messages = (
            this.props.order === 'asc' ?
            this.props.thread.nonEmptyMessages :
            [...this.props.thread.nonEmptyMessages].reverse()
        );
        if (!this.props.showNotificationMessages) {
            messages = messages.filter(
                (msg) => !['user_notification', 'notification'].includes(
                    msg.message_type
                )
            );
        }
        return messages;
    },
});

Thread.props = [
    ...Thread.props,
    'showNotificationMessages?',
];
Thread.defaultProps = {
    ...Thread.defaultProps,
    showNotificationMessages: true,
};