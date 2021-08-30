/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onClickInboxMarkAllAsRead
        [Action/behavior]
            {Message/markAllAsRead}
`;
