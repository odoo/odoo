/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discuss
        [Field/model]
            ThreadViewer
        [Field/type]
            one
        [Field/target]
            Discuss
        [Field/inverse]
            Discuss/threadViewer
        [Field/isReadonly]
            true
`;
