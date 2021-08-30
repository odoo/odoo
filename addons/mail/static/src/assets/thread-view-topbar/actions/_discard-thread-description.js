/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/_discardThreadDescription
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/isEditingThreadDescription]
                        false
                    [ThreadViewTopbar/pendingThreadDescription]
                        {Record/empty}
`;
