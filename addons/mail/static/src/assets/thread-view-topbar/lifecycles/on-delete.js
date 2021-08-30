/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onDelete
        [Lifecycle/model]
            ThreadViewTopbar
        [Lifecycle/behavior]
            {Device/removeEventListener}
                [0]
                    click
                [1]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            ev
                        [Function/out]
                            {ThreadViewTopbar/_onClickCaptureGlobal}
                                @record
                                @ev
                [2]
                    true
`;
