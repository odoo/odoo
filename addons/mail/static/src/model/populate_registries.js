/** @odoo-module **/

import { compute } from '@mail/model/fields/properties/compute/compute';
import { defaultProperty } from '@mail/model/fields/properties/default/default';
import { dependencies } from '@mail/model/fields/properties/dependencies/dependencies';
import { inverse } from '@mail/model/fields/properties/inverse/inverse';
import { isCausal } from '@mail/model/fields/properties/is_causal/is_causal';
import { isMany2X } from '@mail/model/fields/properties/is_many2x/is_many2x';
import { isOnChange } from '@mail/model/fields/properties/is_on_change/is_on_change';
import { isOne2X } from '@mail/model/fields/properties/is_one2x/is_one2x';
import { isX2Many } from '@mail/model/fields/properties/is_x2many/is_x2many';
import { isX2One } from '@mail/model/fields/properties/is_x2one/is_x2one';
import { readonly } from '@mail/model/fields/properties/readonly/readonly';
import { related } from '@mail/model/fields/properties/related/related';
import { required } from '@mail/model/fields/properties/required/required';
import { to } from '@mail/model/fields/properties/to/to';
import { attribute } from '@mail/model/fields/types/attribute/attribute';
import { relation } from '@mail/model/fields/types/relation/relation';
import { factoryActivity } from '@mail/models/activity/activity';
import { factoryActivityType } from '@mail/models/activity_type/activity_type';
import { factoryAttachment } from '@mail/models/attachment/attachment';
import { factoryAttachmentViewer } from '@mail/models/attachment_viewer/attachment_viewer';
import { factoryCannedResponse } from '@mail/models/canned_response/canned_response';
import { factoryChannelCommand } from '@mail/models/channel_command/channel_command';
import { factoryChatWindow } from '@mail/models/chat_window/chat_window';
import { factoryChatWindowManager } from '@mail/models/chat_window_manager/chat_window_manager';
import { factoryChatter } from '@mail/models/chatter/chatter';
import { factoryComposer } from '@mail/models/composer/composer';
import { factoryCountry } from '@mail/models/country/country';
import { factoryDevice } from '@mail/models/device/device';
import { factoryDialog } from '@mail/models/dialog/dialog';
import { factoryDialogManager } from '@mail/models/dialog_manager/dialog_manager';
import { factoryDiscuss } from '@mail/models/discuss/discuss';
import { factoryFollower } from '@mail/models/follower/follower';
import { factoryFollowerSubtype } from '@mail/models/follower_subtype/follower_subtype';
import { factoryFollowerSubtypeList } from '@mail/models/follower_subtype_list/follower_subtype_list';
import { factoryLocale } from '@mail/models/locale/locale';
import { factoryMailTemplate } from '@mail/models/mail_template/mail_template';
import { factoryMessage } from '@mail/models/message/message';
import { factoryMessageSeenIndicator } from '@mail/models/message_seen_indicator/message_seen_indicator';
import { factoryMessaging } from '@mail/models/messaging/messaging';
import { factoryMessagingInitializer } from '@mail/models/messaging_initializer/messaging_initializer';
import { factoryMessagingMenu } from '@mail/models/messaging_menu/messaging_menu';
import { factoryMessagingNotificationHandler } from '@mail/models/messaging_notification_handler/messaging_notification_handler';
import { factoryModel } from '@mail/models/model/model';
import { factoryNotification } from '@mail/models/notification/notification';
import { factoryNotificationGroup } from '@mail/models/notification_group/notification_group';
import { factoryNotificationGroupManager } from '@mail/models/notification_group_manager/notification_group_manager';
import { factoryPartner } from '@mail/models/partner/partner';
import { factorySuggestedRecipientInfo } from '@mail/models/suggested_recipient_info/suggested_recipient_info';
import { factoryThread } from '@mail/models/thread/thread';
import { factoryThreadCache } from '@mail/models/thread_cache/thread_cache';
import { factoryThreadPartnerSeenInfo } from '@mail/models/thread_partner_seen_info/thread_partner_seen_info';
import { factoryThreadView } from '@mail/models/thread_view/thread_view';
import { factoryThreadViewer } from '@mail/models/thread_view/thread_viewer';
import { factoryUser } from '@mail/models/user/user';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    const properties = [
        ['compute', compute],
        ['default', defaultProperty],
        ['dependencies', dependencies],
        ['inverse', inverse],
        ['isCausal', isCausal],
        ['isMany2X', isMany2X],
        ['isOnChange', isOnChange],
        ['isOne2X', isOne2X],
        ['isX2Many', isX2Many],
        ['isX2One', isX2One],
        ['readonly', readonly],
        ['related', related],
        ['required', required],
        ['to', to],
    ];
    for (const [name, property] of properties) {
        env.modelManager.fieldPropertyRegistry.set(name, property);
    }
    const types = [
        ['attribute', attribute],
        ['relation', relation],
    ];
    for (const [name, type] of types) {
        env.modelManager.fieldTypeRegistry.set(name, type);
    }
    const models = [
        ['mail.model', factoryModel], // base model, must be first on the list
        ['mail.activity', factoryActivity],
        ['mail.activity_type', factoryActivityType],
        ['mail.attachment', factoryAttachment],
        ['mail.attachment_viewer', factoryAttachmentViewer],
        ['mail.canned_response', factoryCannedResponse],
        ['mail.channel_command', factoryChannelCommand],
        ['mail.chat_window', factoryChatWindow],
        ['mail.chat_window_manager', factoryChatWindowManager],
        ['mail.chatter', factoryChatter],
        ['mail.composer', factoryComposer],
        ['mail.country', factoryCountry],
        ['mail.device', factoryDevice],
        ['mail.dialog', factoryDialog],
        ['mail.dialog_manager', factoryDialogManager],
        ['mail.discuss', factoryDiscuss],
        ['mail.follower', factoryFollower],
        ['mail.follower_subtype', factoryFollowerSubtype],
        ['mail.follower_subtype_list', factoryFollowerSubtypeList],
        ['mail.locale', factoryLocale],
        ['mail.mail_template', factoryMailTemplate],
        ['mail.message', factoryMessage],
        ['mail.message_seen_indicator', factoryMessageSeenIndicator],
        ['mail.messaging', factoryMessaging],
        ['mail.messaging_initializer', factoryMessagingInitializer],
        ['mail.messaging_menu', factoryMessagingMenu],
        ['mail.messaging_notification_handler', factoryMessagingNotificationHandler],
        ['mail.notification', factoryNotification],
        ['mail.notification_group', factoryNotificationGroup],
        ['mail.notification_group_manager', factoryNotificationGroupManager],
        ['mail.partner', factoryPartner],
        ['mail.suggested_recipient_info', factorySuggestedRecipientInfo],
        ['mail.thread', factoryThread],
        ['mail.thread_cache', factoryThreadCache],
        ['mail.thread_partner_seen_info', factoryThreadPartnerSeenInfo],
        ['mail.thread_view', factoryThreadView],
        ['mail.thread_viewer', factoryThreadViewer],
        ['mail.user', factoryUser],
    ];
    for (const [name, model] of models) {
        env.modelManager.registerModel(name, model);
    }
}


