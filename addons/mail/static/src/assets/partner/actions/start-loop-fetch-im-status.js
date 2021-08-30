/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/startLoopFetchImStatus
        [Action/behavior]
            {Partner/_fetchImStatus}
            {Partner/_loopFetchImStatus}
`;
