/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL component of this option list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            RtcOptionList
        [Field/type]
            attr
        [Field/target]
            RtcOptionListComponent
        [Field/inverse]
            RtcOptionListComponent/rtcOptionList
`;
