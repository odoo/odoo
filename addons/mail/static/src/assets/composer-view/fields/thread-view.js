/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread view on which this composer allows editing (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadView
        [Field/model]
            ComposerView
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/isReadonly]
            true
        [Field/inverse]
            ThreadView/composerView
`;
