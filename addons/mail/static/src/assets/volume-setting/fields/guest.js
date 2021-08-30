/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guest
        [Field/model]
            VolumeSetting
        [Field/type]
            one
        [Field/target]
            Guest
        [Field/inverse]
            Guest/volumeSetting
`;
