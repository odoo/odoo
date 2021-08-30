/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            onChangeLastSeenByCurrentPartnerMessageId
        [onChange/model]
            Thread
        [onChange/dependencies]
            Thread/lastSeenByCurrentPartnerMessageId
        [onChange/behavior]
            {Env/messagingBus}
            .{Bus/trigger}
                [0]
                    o-thread-last-seen-by-current-partner-message-id-changed
                [1]
                    [thread]
                        @record
`;
