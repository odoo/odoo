/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message is clicked. When message is in
        clicked state, it keeps displaying actions even if not hovered.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isClicked
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
