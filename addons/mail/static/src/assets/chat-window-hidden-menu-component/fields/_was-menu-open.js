/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The intent of the toggle button depends on the last rendered state.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _wasMenuOpen
        [Field/model]
            ChatWindowHiddenMenuComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
