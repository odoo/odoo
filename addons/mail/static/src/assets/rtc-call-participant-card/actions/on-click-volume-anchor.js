/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handled by the popover component.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallParticipantCard/onClickVolumeAnchor
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcCallParticipantCard
        [Action/behavior]
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    CallParticipantCard.clickVolumeAnchor
`;
