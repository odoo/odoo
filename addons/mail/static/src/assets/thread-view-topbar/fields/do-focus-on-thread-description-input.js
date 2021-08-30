/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread description input needs to be focused.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doFocusOnThreadDescriptionInput
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
