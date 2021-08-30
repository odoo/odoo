/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowHiddenMenuComponent/_apply
        [Action/params]
            record
        [Action/behavior]
            {ChatWindowHiddenMenuComponent/_applyListHeight}
                @record
            {ChatWindowHiddenMenuComponent/_applyOffset}
                @record
            {Record/update}
                [0]
                    @record
                [1]
                    [ChatWindowHiddenMenuComponent/_wasMenuOpen]
                        {ChatWindowManager/isHiddenMenuOpen}
`;
