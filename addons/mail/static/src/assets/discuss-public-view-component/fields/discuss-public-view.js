/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussPublicView
        [Field/model]
            DiscussPublicViewComponent
        [Field/type]
            one
        [Field/target]
            DiscussPublicView
        [Field/isRequired]
            true
`;
