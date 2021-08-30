/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatWindowManagerComponent
        [Model/template]
            root
                {Dev/comment}
                    Note: DOM elements are ordered from left to right
                hiddenMenu
                chatWindowForeach
`;
