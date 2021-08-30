/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadPreviewViews
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            ThreadPreviewView
        [Field/inverse]
            ThreadPreviewView/thread
        [Field/isCausal]
            true
`;
