/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the current partner is mentioned.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCurrentPartnerMentioned
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {Collection/includes}
                [0]
                    @record
                    .{Message/recipients}
                [1]
                    {Env/currentPartner}
`;
