/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            subtype
        [Field/model]
            FollowerSubtypeListComponent:subtype
        [Field/type]
            one
        [Field/target]
            FollowerSubtype
        [Field/isRequired]
            true
`;
