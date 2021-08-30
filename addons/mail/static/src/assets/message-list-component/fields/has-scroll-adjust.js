/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasScrollAdjust
        [Field/model]
            MessageListComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            true
`;
