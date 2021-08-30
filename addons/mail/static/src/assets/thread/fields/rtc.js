/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, the current thread is the thread that hosts the current RTC call.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtc
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Rtc
        [Field/inverse]
            Rtc/channel
`;
