/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            messageContainer
        [Context/model]
            MessageListComponent
        [Model/fields]
            messageView
        [Model/template]
            messageContainerForeach
                messageContainer
                    separatorNewMessages
                        separatorLineNewMessages
                        separatorLabelNewMessages
                    separatorDate
                        separatorDateLineStart
                        separatorLabelDate
                        separatorDateLineEnd
                    message
`;
