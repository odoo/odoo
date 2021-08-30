/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationVolumeSettingUpdate
        [Action/params]
            volumeSettings
                [type]
                    Object
        [Action/behavior]
            {Record/update}
                [0]
                    {Env/userSetting}
                [1]
                    [UserSetting/volumeSettings]
                        @volumeSettings
`;
