/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'ThreadViewer' currently managing 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViewer
        [Field/model]
            ThreadView
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            ThreadView/threadView
`;
