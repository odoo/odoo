/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This listens to the right click event, and used to redirect the event
        as a click on the popover.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallParticipantCardComponent/_onContextmenu
        [Action/params]
            ev
                [type]
                    web.Event
            record
                [type]
                    RtcCallParticipantCardComponent
        [Action/behavior]
            {web.Event/preventDefault}
                @ev
            {UI/click}
                @record
                .{RtcCallParticipantCardComponent/volumeMenuAnchor}
`;
