/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            count
        [Field/model]
            MessageReactionGroup
        [Field/type]
            attr
        [Field/isRequired]
            true
`;
