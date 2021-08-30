/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the name of the given member in the member list of
        this channel.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/onClickMemberName
        [Action/params]
            record
                [type]
                    Thread
            member
                [type]
                    Partner
        [Action/behavior]
            {Partner/openProfile}
                @member
`;
