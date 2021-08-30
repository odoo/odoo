/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatter
        [Field/model]
            ChatterTopbarComponent
        [Field/type]
            one
        [Field/target]
            Chatter
        [Field/isRequired]
            true
`;
