/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Token to identify the session, it is currently just the toString
        id of the record.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            peerToken
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            @record
            .{RtcSession/id}
`;
