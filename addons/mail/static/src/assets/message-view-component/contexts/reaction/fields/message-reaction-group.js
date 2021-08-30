/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageReactionGroup
        [Field/model]
            MessageViewComponent:reaction
        [Field/type]
            one
        [Field/target]
            MessageReactionGroup
        [Field/isRequired]
            true
`;
