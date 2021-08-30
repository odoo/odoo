/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the cancel link.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/onClickCancelLink
        [Action/params]
            record
                [type]
                    ComposerView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {web.Event/preventDefault}
                @ev
            {ComposerView/discard}
                @record
`;
