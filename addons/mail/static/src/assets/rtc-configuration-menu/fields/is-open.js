/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isOpen
        [Field/model]
            RtcConfigurationMenu
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
