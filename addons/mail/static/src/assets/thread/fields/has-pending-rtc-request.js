/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether there is a server request for joining or leaving the RTC session.
        TODO Should maybe be on messaging (after messaging env rebase) to lock the
        rpc across all threads.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasPendingRtcRequest
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
