/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatWindowHiddenMenuComponent
        [Model/fields]
            device
            _wasMenuOpen
        [Model/template]
            root
                dropdownToggle
                    dropdownToggleIcon
                    windowCounter
                list
                    listItemForeach
                unreadCounter
        [Model/actions]
            ChatWindowHiddenMenuComponent/_apply
            ChatWindowHiddenMenuComponent/_applyListHeight
            ChatWindowHiddenMenuComponent/_applyOffset
        [Model/lifecycles]
            onUpdate
`;
