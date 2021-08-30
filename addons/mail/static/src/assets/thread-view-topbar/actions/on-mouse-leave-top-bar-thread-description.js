/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles mouseleave on the "thread description" of this top bar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onMouseLeaveTopBarThreadDescription
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/isMouseOverThreadDescription]
                        false
`;
