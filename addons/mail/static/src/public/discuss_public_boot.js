/** @odoo-module **/

import { insert } from '@mail/model/model_field_command';
import { MessagingService } from '@mail/services/messaging/messaging';
import { getMessagingComponent } from '@mail/utils/messaging_component';

import { processTemplates } from '@web/core/assets';
import { registry } from '@web/core/registry';
import { makeEnv, startServices } from '@web/env';
import { session } from '@web/session';

import * as AbstractService from 'web.AbstractService';
import { serviceRegistry as legacyServiceRegistry } from 'web.core';
import * as legacyEnv from 'web.env';
import {
    makeLegacyCrashManagerService,
    makeLegacyDialogMappingService,
    makeLegacyNotificationService,
    makeLegacyRpcService,
    makeLegacySessionService,
    mapLegacyEnvToWowlEnv,
} from '@web/legacy/utils';
import * as legacySession from 'web.session';

owl.Component.env = legacyEnv;

export async function boot() {
    await owl.utils.whenReady();
    owl.config.mode = owl.Component.env.isDebug() ? 'dev' : 'prod';
    AbstractService.prototype.deployServices(owl.Component.env);
    const serviceRegistry = registry.category('services');
    serviceRegistry.add('legacy_rpc', makeLegacyRpcService(owl.Component.env));
    serviceRegistry.add('legacy_session', makeLegacySessionService(owl.Component.env, legacySession));
    serviceRegistry.add('legacy_notification', makeLegacyNotificationService(owl.Component.env));
    serviceRegistry.add('legacy_crash_manager', makeLegacyCrashManagerService(owl.Component.env));
    serviceRegistry.add('legacy_dialog_mapping', makeLegacyDialogMappingService(owl.Component.env));
    await legacySession.is_bound;
    owl.Component.env.qweb.addTemplates(legacySession.owlTemplates);
    Object.assign(odoo, {
        info: {
            db: session.db,
            server_version: session.server_version,
            server_version_info: session.server_version_info,
            isEnterprise: session.server_version_info.slice(-1)[0] === 'e',
        },
        isReady: false,
    });
    const env = makeEnv();
    const [, templates] = await Promise.all([
        startServices(env),
        odoo.loadTemplatesPromise.then(processTemplates),
    ]);
    env.qweb.addTemplates(templates);
    mapLegacyEnvToWowlEnv(owl.Component.env, env);
    odoo.isReady = true;
    legacyServiceRegistry.add('messaging', MessagingService.extend({
        messagingValues: {
            autofetchPartnerImStatus: false,
        },
    }));

    async function createThreadViewFromChannelData(channelData) {
        const messaging = await owl.Component.env.services.messaging.get();
        const threadViewer = messaging.models['mail.thread_viewer'].create({
            extraClass: 'flex-grow-1',
            hasMemberList: true,
            hasThreadView: true,
            hasTopbar: true,
            thread: insert(messaging.models['mail.thread'].convertData(channelData)),
        });
        const ThreadView = getMessagingComponent('ThreadView');
        const threadViewComponent = new ThreadView(null, {
            composerAttachmentsDetailsMode: 'card',
            hasComposer: true,
            hasComposerThreadTyping: true,
            threadViewLocalId: threadViewer.threadView.localId,
        });
        await threadViewComponent.mount(document.body);
        if (threadViewer.thread.defaultDisplayMode === 'video_full_screen') {
            await threadViewer.thread.toggleCall({ startWithVideo: true });
            // TODO full screen not possible until the user actually makes an action on the page
        }
    }

    async function createWelcomeView(channelId) {
        const messaging = await owl.Component.env.services.messaging.get();
        const WelcomeView = getMessagingComponent('WelcomeView');
        const welcomeView = messaging.models['mail.welcome_view'].create({
            channelId,
            isDoFocusGuestNameInput: true,
            pendingGuestName: messaging.currentGuest && messaging.currentGuest.name,
        });
        const welcomeViewComponent = new WelcomeView(null, {
            localId: welcomeView.localId,
        });
        await welcomeViewComponent.mount(document.body);
    }

    return { createThreadViewFromChannelData, createWelcomeView };
}
