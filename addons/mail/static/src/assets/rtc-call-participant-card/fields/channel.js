/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The channel of the call.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channel
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isRequired]
            true
`;
