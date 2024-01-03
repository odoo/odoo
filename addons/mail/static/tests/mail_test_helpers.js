/** @odoo-module */

import { busModels } from "@bus/../tests/bus_test_helpers";
import { defineModels, webModels } from "@web/../tests/web_test_helpers";
import { Base } from "./mock_server/mock_models/base";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { DiscussChannelMember } from "./mock_server/mock_models/discuss_channel_member";
import { DiscussChannelRtcSession } from "./mock_server/mock_models/discuss_channel_rtc_session";
import { DiscussGifFavorite } from "./mock_server/mock_models/discuss_gif_favorite";
import { DiscussVoiceMetadata } from "./mock_server/mock_models/discuss_voice_metadata";
import { IrAttachment } from "./mock_server/mock_models/ir_attachment";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";
import { M2xAvatarUser } from "./mock_server/mock_models/m2x_avatar_user";
import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { MailActivityType } from "./mock_server/mock_models/mail_activity_type";
import { MailFollowers } from "./mock_server/mock_models/mail_followers";
import { MailGuest } from "./mock_server/mock_models/mail_guest";
import { MailLinkPreview } from "./mock_server/mock_models/mail_link_preview";
import { MailMessage } from "./mock_server/mock_models/mail_message";
import { MailMessageReaction } from "./mock_server/mock_models/mail_message_reaction";
import { MailMessageSubtype } from "./mock_server/mock_models/mail_message_subtype";
import { MailNotification } from "./mock_server/mock_models/mail_notification";
import { MailShortcode } from "./mock_server/mock_models/mail_shortcode";
import { MailTemplate } from "./mock_server/mock_models/mail_template";
import { MailThread } from "./mock_server/mock_models/mail_thread";
import { MailTrackingValue } from "./mock_server/mock_models/mail_tracking_value";
import { ResFake } from "./mock_server/mock_models/res_fake";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { ResUsersSettings } from "./mock_server/mock_models/res_users_settings";
import { ResUsersSettingsVolumes } from "./mock_server/mock_models/res_users_settings_volumes";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function defineMailModels() {
    return defineModels({ ...webModels, ...busModels, ...mailModels });
}

export const mailModels = {
    Base,
    DiscussChannel,
    DiscussChannelMember,
    DiscussChannelRtcSession,
    DiscussGifFavorite,
    DiscussVoiceMetadata,
    IrAttachment,
    IrWebSocket,
    M2xAvatarUser,
    MailActivity,
    MailActivityType,
    MailFollowers,
    MailGuest,
    MailLinkPreview,
    MailMessage,
    MailMessageReaction,
    MailMessageSubtype,
    MailNotification,
    MailShortcode,
    MailTemplate,
    MailThread,
    MailTrackingValue,
    ResFake,
    ResPartner,
    ResUsers,
    ResUsersSettings,
    ResUsersSettingsVolumes,
};
