/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            name
        [Field/model]
            FollowerSubtype
        [Field/type]
            attr
        [Field/target]
            String
`;
