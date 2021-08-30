/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            cannedResponses
        [Field/model]
            Env
        [Field/type]
            many
        [Field/target]
            CannedResponse
`;
