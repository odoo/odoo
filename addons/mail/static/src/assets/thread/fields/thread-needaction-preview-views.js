/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadNeedactionPreviewViews
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            ThreadNeedactionPreviewView
        [Field/inverse]
            ThreadNeedactionPreviewView/thread
        [Field/isCausal]
            true
`;
