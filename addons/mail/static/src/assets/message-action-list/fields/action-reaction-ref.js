/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the reference to the reaction action in the component.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            actionReactionRef
        [Field/model]
            MessageActionList
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            MessageActionList/messageActionListComponents
            Collection/first
            MessageActionListComponent/actionReaction
`;
