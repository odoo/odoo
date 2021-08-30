/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcOptionList
        [Field/model]
            RtcController
        [Field/type]
            one
        [Field/target]
            RtcOptionList
        [Field/inverse]
            RtcOptionList/rtcController
        [Field/isCausal]
            true
        [Field/default]
            {Record/insert}
                [Record/models]
                    RtcOptionList
`;
