/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the delete message confirm view that is displaying this
        message view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            deleteMessageConfirmViewOwner
        [Field/model]
            MessageView
        [Field/type]
            one
        [Field/target]
            DeleteMessageConfirmView
        [Field/isReadonly]
            true
        [Field/inverse]
            DeleteMessageConfirmView/messageView
`;
