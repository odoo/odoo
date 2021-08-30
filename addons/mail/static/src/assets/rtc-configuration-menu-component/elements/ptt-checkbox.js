/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttCheckbox
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            input
        [web.Element/type]
            checkbox
        [web.Element/aria-label]
            {Locale/text}
                Toggle Push-to-talk
        [web.Element/title]
            {Locale/text}
                Toggle Push-to-talk
        [Element/onChange]
            {RtcConfigurationMenuComponent/onChangePushToTalk}
                [0]
                    @record
                [1]
                    @ev
        [web.Element/isChecked]
            {Env/userSetting}
            .{UserSetting/usePushToTalk}
`;
