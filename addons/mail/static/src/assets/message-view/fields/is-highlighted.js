/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether the message should be forced to be isHighlighted. Should only
        be set through @see MessageView/highlight
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isHighlighted
        [Field/model]
            MessageView
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
