/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Groups of reactions per content allowing to know the number of
        reactions for each.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageReactionGroups
        [Field/model]
            Message
        [Field/type]
            many
        [Field/target]
            MessageReactionGroup
        [Field/inverse]
            MessageReactionGroup/message
        [Field/isCausal]
            true
`;
