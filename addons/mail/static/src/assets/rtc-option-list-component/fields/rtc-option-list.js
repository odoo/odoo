/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcOptionList
        [Field/model]
            RtcOptionListComponent
        [Field/type]
            one
        [Field/target]
            RtcOptionList
        [Field/isRequired]
            true
        [Field/inverse]
            RtcOptionList/component
`;
