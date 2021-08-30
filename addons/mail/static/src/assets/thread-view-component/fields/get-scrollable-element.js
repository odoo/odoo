/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Function returns the exact scrollable element from the parent
        to manage proper scroll heights which affects the load more messages.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            getScrollableElement
        [Field/model]
            ThreadViewComponent
        [Field/type]
            attr
        [Field/target]
            Function
`;
