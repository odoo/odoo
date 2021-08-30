/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The keyword to use a specific canned response.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            source
        [Field/model]
            CannedResponse
        [Field/type]
            attr
        [Field/target]
            String
`;
