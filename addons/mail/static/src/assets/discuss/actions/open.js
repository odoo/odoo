/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Discuss/open
        [Action/params]
            record
                [type]
                    Discuss
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [Discuss/discussView]
                        {Record/insert}
                            [Record/models]
                                DiscussView
`;
