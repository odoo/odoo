/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            ThreadNeedactionPreviewView
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            Thread/threadNeedactionPreviewViews
`;
