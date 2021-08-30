/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread name input needs to be focused.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doFocusOnThreadNameInput
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
