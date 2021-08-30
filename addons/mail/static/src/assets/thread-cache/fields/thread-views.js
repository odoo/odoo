/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the 'ThreadView' that are currently displaying 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViews
        [Field/model]
            ThreadCache
        [Field/type]
            many
        [Field/target]
            ThreadView
        [Field/inverse]
            ThreadView/threadCache
`;
