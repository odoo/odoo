/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        id of the current timeout that will reset isHighlighted to false.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            highlightTimeout
        [Field/model]
            MessageView
        [Field/type]
            attr
        [Field/target]
            Integer
`;
