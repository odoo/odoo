/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onCreate
        [Lifecycle/model]
            ThreadViewTopbar
        [Lifecycle/behavior]
            {Device/addEventListener}
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
                                true
                [2]
                    true
`;
