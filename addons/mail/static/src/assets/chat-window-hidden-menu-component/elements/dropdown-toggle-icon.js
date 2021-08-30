/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dropdownToggleIcon
        [Element/model]
            ChatWindowHiddenMenuComponent
        [Record/models]
            ChatWindowHiddenMenuComponent/dropdownToggleItem
        [web.Element/class]
            fa
            fa-comments-o
`;
