/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/_loopFetchImStatus
        [Action/behavior]
            {Browser/setTimeout}
                [0]
                    {Partner/_fetchImStatus}
                    {Partner/_loopFetchImStatus}
                [1]
                    50000
`;
