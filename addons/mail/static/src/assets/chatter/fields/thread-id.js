/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the id of the thread that will be displayed by 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadId
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            Number
`;
