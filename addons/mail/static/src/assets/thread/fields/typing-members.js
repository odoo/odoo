/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Members that are currently typing something in the composer of this
        thread, including current partner.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            typingMembers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
`;
