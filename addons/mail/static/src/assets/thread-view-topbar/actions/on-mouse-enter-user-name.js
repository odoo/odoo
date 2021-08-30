/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles mouseenter on the "user name" of this top bar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onMouseEnterUserName
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/isMouseOverUserName]
                        true
`;
