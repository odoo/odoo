/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the member list of this chat window is opened.
        Only makes sense if this thread hasMemberListFeature is true.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMemberListOpened
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
