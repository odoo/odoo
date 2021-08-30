/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/getNextPublicId
        [Action/feature]
            im_livechat
        [Action/behavior]
            :nextPublicId
                -1
            {Record/insert}
                [Record/models]
                    Function
                :id
                    @nextPublicId
                :nextPublicId
                    @nextPublicId
                    .{-}
                        1
                @id
`;
