/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the member list of this thread is opened.
        Only makes sense if hasMemberListFeature and hasMemberList are true.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMemberListOpened
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
