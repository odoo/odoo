/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the most appropriate view that is a profile for this partner.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/openProfile
        [Action/params]
            partner
                [type]
                    Partner
        [Action/behavior]
            {Env/openDocument}
                [id]
                    @partner
                    .{Partner/id}
                [model]
                    res.partner
`;
