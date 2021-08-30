/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether the cursor is currently over this thread name in
        the top bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMouseOverThreadName
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
