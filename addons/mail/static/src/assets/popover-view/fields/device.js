/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            device
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            Device
        [Field/observe]
            {Record/insert}
                [Record/models]
                    FieldObserver
                [event]
                    click
                [callback]
                    {PopoverView/_onClickCaptureGlobal}
                        [0]
                            @record
                        [1]
                            @ev
`;
