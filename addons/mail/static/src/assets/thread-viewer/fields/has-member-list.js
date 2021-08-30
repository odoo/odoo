/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread viewer has a member list.
        Only makes sense if this thread is a channel and if the channel is
        not a chat.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasMemberList
        [Field/model]
            ThreadViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
