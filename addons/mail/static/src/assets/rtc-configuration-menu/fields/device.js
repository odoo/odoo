/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            device
        [Field/model]
            RtcConfigurationMenu
        [Field/type]
            one
        [Field/target]
            Device
        [Field/default]
            {Env/device}
        [Field/observe]
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    keydown
                [FieldObserver/callback]
                    {RtcConfigurationMenu/_onKeydown}
                        @record
                        @ev
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    keydown
                [FieldObserver/callback]
                    {RtcConfigurationMenu/_onKeyup}
                        @record
                        @ev
`;
