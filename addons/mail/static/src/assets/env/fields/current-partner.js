/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            currentPartner
        [Field/model]
            Env
        [Field/type]
            one
        [Field/target]
            Partner
`;
