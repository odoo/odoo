/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessagingNotificationHandler
        [Model/id]
            MessagingNotificationHandler/messaging
        [Model/actions]
            MessagingNotificationHandler/_handleNotification
            MessagingNotificationHandler/_handleNotificationAttachmentDelete
            MessagingNotificationHandler/_handleNotificationChannelJoined
            MessagingNotificationHandler/_handleNotificationChannelLastInterestDateTimeChanged
            MessagingNotificationHandler/_handleNotificationChannelLeave
            MessagingNotificationHandler/_handleNotificationChannelMessage
            MessagingNotificationHandler/_handleNotificationChannelPartnerFetched
            MessagingNotificationHandler/_handleNotificationChannelPartnerSeen
            MessagingNotificationHandler/_handleNotificationChannelPartnerTypingStatus
            MessagingNotificationHandler/_handleNotificationChannelUnpin
            MessagingNotificationHandler/_handleNotificationChannelUpdate
            MessagingNotificationHandler/_handleNotificationNeedaction
            MessagingNotificationHandler/_handleNotificationMessageDelete
            MessagingNotificationHandler/_handleNotificationPartnerMessageNotificationUpdate
            MessagingNotificationHandler/_handleNotificationPartnerMarkAsRead
            MessagingNotificationHandler/_handleNotificationPartnerToggleStar
            MessagingNotificationHandler/_handleNotificationPartnerTransientMessage
            MessagingNotificationHandler/_handleNotificationPartnerUserConnection
            MessagingNotificationHandler/_handleNotificationResUsersSettings
            MessagingNotificationHandler/_handleNotificationRtcPeerToPeer
            MessagingNotificationHandler/_handleNotificationRtcSessionEnded
            MessagingNotificationHandler/_handleNotificationRtcSessionUpdate
            MessagingNotificationHandler/_handleNotificationSimpleNotification
            MessagingNotificationHandler/_handleNotificationVolumeSettingUpdate
            MessagingNotificationHandler/_handleNotifications
            MessagingNotificationHandler/_notifyNewChannelMessageWhileOutOfFocus
            MessagingNotificationHandler/_notifyThreadViewsMessageReceived
            MessagingNotificationHandler/start
            MessagingNotificationHandler/stop
`;
