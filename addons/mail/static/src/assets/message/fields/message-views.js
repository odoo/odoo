/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the views that are displaying this message.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageViews
        [Field/model]
            Message
        [Field/type]
            many
        [Field/target]
            MessageView
        [Field/isCausal]
            true
        [Field/inverse]
            MessageView/message
`;
