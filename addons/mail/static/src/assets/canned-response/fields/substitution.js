/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The canned response itself which will replace the keyword previously
        entered.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            substitution
        [Field/model]
            CannedResponse
        [Field/type]
            attr
        [Field/target]
            String
`;
