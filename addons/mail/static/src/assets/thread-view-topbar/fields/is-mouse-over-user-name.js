/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether the cursor is currently over the user name in this
        top bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMouseOverUserName
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
