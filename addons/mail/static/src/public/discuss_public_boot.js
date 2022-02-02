/** @odoo-module **/

import { data } from 'mail.discuss_public_channel_template';

import { MessagingService } from '@mail/services/messaging/messaging';
import { getMessagingComponent } from '@mail/utils/messaging_component';

import { processTemplates } from '@web/core/assets';
import { MainComponentsContainer } from '@web/core/main_components_container';
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

const { App, Component, mount, whenReady } = owl;

Component.env = legacyEnv;

(async function boot() {
    await whenReady();
    AbstractService.prototype.deployServices(Component.env);
    const serviceRegistry = registry.category('services');
    serviceRegistry.add('legacy_rpc', makeLegacyRpcService(Component.env));
    serviceRegistry.add('legacy_session', makeLegacySessionService(Component.env, legacySession));
    serviceRegistry.add('legacy_notification', makeLegacyNotificationService(Component.env));
    serviceRegistry.add('legacy_crash_manager', makeLegacyCrashManagerService(Component.env));
    serviceRegistry.add('legacy_dialog_mapping', makeLegacyDialogMappingService(Component.env));
    await legacySession.is_bound;
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
    mapLegacyEnvToWowlEnv(Component.env, env);
    odoo.isReady = true;
    legacyServiceRegistry.add('messaging', MessagingService.extend({
        messagingValues: {
            autofetchPartnerImStatus: false,
        },
    }));
    await mount(MainComponentsContainer, document.body, { env, templates });
    createAndMountDiscussPublicView();
})();

async function createAndMountDiscussPublicView() {
    const messaging = await Component.env.services.messaging.get();
    // needed by the attachment viewer
    const DialogManager = getMessagingComponent('DialogManager');
    await mount(DialogManager, document.body, {
        templates: legacySession.owlTemplates,
        env: Component.env,
    });
    messaging.models['Thread'].insert(messaging.models['Thread'].convertData(data.channelData));
    const discussPublicView = messaging.models['DiscussPublicView'].create(data.discussPublicViewData);
    if (discussPublicView.shouldDisplayWelcomeViewInitially) {
        discussPublicView.switchToWelcomeView();
    } else {
        discussPublicView.switchToThreadView();
    }
    const DiscussPublicView = getMessagingComponent('DiscussPublicView');
    await mount(DiscussPublicView, document.body, {
        templates: legacySession.owlTemplates,
        env: Component.env,
        props: {
            localId: discussPublicView.localId,
        },
    });
}
