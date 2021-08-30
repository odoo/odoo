/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            chatWindow
        [Context/model]
            ChatWindowManagerComponent
        [Model/fields]
            chatWindow
        [Model/template]
            chatWindowForeach
                chatWindow
`;
