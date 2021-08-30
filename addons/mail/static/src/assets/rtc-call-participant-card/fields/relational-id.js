/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Unique id for this session provided when instantiated.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            relationalId
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
