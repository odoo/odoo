/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatter
        [Field/model]
            ChatterComponent
        [Field/type]
            one
        [Field/target]
            Chatter
        [Field/isRequired]
            true
        [Field/inverse]
            Chatter/component
`;
