/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Close the messaging menu. Should reset its internal state.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingMenu/close
        [Action/params]
            messagingMenu
                [type]
                    MessagingMenu
        [Action/behavior]
            {Record/update}
                [0]
                    @messagingMenu
                [1]
                    [MessagingMenu/isOpen]
                        false
`;
