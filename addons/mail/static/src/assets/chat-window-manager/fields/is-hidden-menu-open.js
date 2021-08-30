/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isHiddenMenuOpen
        [Field/model]
            ChatWindowManager
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
