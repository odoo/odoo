/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this' should automatically scroll on receiving
        a new message. Detection of new message is done through the component
        hint 'message-received'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasAutoScrollOnMessageReceived
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            true
`;
