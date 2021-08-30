/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this message view should be highlighted at next
        render. Scrolls into view and briefly highlights it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doHighlight
        [Field/model]
            MessageView
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
