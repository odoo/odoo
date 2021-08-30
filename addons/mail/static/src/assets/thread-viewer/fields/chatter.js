/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatter
        [Field/model]
            ThreadViewer
        [Field/type]
            one
        [Field/target]
            Chatter
        [Field/inverse]
            Chatter/threadViewer
        [Field/isReadonly]
            true
`;
