/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            visitor
        [Field/model]
            VisitorBannerComponent
        [Field/type]
            one
        [Field/target]
            Visitor
        [Field/isRequired]
            true
`;
