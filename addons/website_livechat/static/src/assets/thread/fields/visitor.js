/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Visitor connected to the livechat.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            visitor
        [Field/feature]
            website_livechat
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Visitor
        [Field/inverse]
            Visitor/threads
`;
