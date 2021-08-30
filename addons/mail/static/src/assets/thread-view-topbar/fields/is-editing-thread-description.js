/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread description is currently being changed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isEditingThreadDescription
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
