/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether this device has a small size (note: this field name is not ideal).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMobile
        [Field/model]
            Device
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
