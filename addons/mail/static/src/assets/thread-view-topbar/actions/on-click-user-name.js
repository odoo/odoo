/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the guest name.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onClickUserName
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {if}
                {Env/isCurrentUserGuest}
                .{isFalsy}
            .{then}
                {break}
            :selection
                {Browser/getSelection}
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/doFocusOnGuestNameInput]
                        true
                    [ThreadViewTopbar/doSetSelectionDirectionOnGuestNameInput]
                        {if}
                            @selection
                            .{Selection/anchorOffset}
                            .{<}
                                @selection
                                .{Selection/focusOffset}
                        .{then}
                            forward
                        .{else}
                            backward
                    [ThreadViewTopbar/doSetSelectionEndOnGuestNameInput]
                        {Math/max}
                            [0]
                                @selection
                                .{Selection/focusOffset}
                            [1]
                                @selection
                                .{Selection/anchorOffset}
                    [ThreadViewTopbar/doSetSelectionStartOnGuestNameInput]
                        {Math/min}
                            [0]
                                @selection
                                .{Selection/focusOffset}
                            [1]
                                @selection
                                .{Selection/anchorOffset}
                    [ThreadViewTopbar/isEditingGuestName]
                        true
                    [ThreadViewTopbar/isMouseOverUserName]
                        false
                    [ThreadViewTopbar/pendingGuestName]
                        {Env/currentGuest}
                        .{Guest/name}
`;
