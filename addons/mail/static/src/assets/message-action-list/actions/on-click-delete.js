/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageActionList/onClickDelete
        [Action/params]
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [MessageActionList/deleteConfirmDialog]
                        {Record/insert}
                            [Record/models]
                                Dialog
`;
