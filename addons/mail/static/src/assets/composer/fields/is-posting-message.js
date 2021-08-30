/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether a post_message request is currently pending.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isPostingMessage
        [Field/model]
            Composer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
