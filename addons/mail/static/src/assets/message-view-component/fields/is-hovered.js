/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message is hovered. When message is hovered
        it displays message actions.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isHovered
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
