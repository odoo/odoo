/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on download icon.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Attachment/onClickDownload
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    Attachment
        [Action/behavior]
            {web.Event/stopPropagation}
                @ev
            {Attachment/download}
                @record

`;
