/** @odoo-module **/

import { data } from 'mail.discuss_public_channel_template';
import { messagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { DiscussPublicViewContainer } from '@mail/components/discuss_public_view_container/discuss_public_view_container';
import { PopoverManagerContainer } from '@mail/components/popover_manager_container/popover_manager_container';
import { messagingService } from '@mail/services/messaging_service';

import { MainComponentsContainer } from '@web/core/main_components_container';
import { registry } from '@web/core/registry';
import { makeEnv, startServices } from '@web/env';
import {
    makeLegacyCrashManagerService,
    makeLegacyDialogMappingService,
    makeLegacyNotificationService,
    makeLegacyRpcService,
    makeLegacySessionService,
    mapLegacyEnvToWowlEnv,
} from '@web/legacy/utils';
import { session } from '@web/session';
import { templates } from '@web/core/assets';

import * as AbstractService from 'web.AbstractService';
import * as legacyEnv from 'web.env';
import * as legacySession from 'web.session';

const { Component, mount, whenReady } = owl;

Component.env = legacyEnv;

(async function boot() {
    await whenReady();

    const messagingValuesService = {
        start() {
            return {};
        }
    };

    AbstractService.prototype.deployServices(Component.env);
    const serviceRegistry = registry.category('services');
    serviceRegistry.add('legacy_rpc', makeLegacyRpcService(Component.env));
    serviceRegistry.add('legacy_session', makeLegacySessionService(Component.env, legacySession));
    serviceRegistry.add('legacy_notification', makeLegacyNotificationService(Component.env));
    serviceRegistry.add('legacy_crash_manager', makeLegacyCrashManagerService(Component.env));
    serviceRegistry.add('legacy_dialog_mapping', makeLegacyDialogMappingService(Component.env));

    serviceRegistry.add('messaging', messagingService);
    serviceRegistry.add('messagingValues', messagingValuesService);

    registry.category('wowlToLegacyServiceMappers').add('make_messaging_to_legacy_env', messagingToLegacyEnv);

    const mainComponentsRegistry = registry.category('main_components');
    mainComponentsRegistry.add('DiscussPublicViewContainer', { Component: DiscussPublicViewContainer, props: { data } });
    // needed by the attachment viewer
    mainComponentsRegistry.add('DialogManagerContainer', { Component: DialogManagerContainer });
    mainComponentsRegistry.add('PopoverManagerContainer', { Component: PopoverManagerContainer });

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
    await startServices(env);
    mapLegacyEnvToWowlEnv(Component.env, env);
    odoo.isReady = true;
    await mount(MainComponentsContainer, document.body, { env, templates, dev: env.debug });
})();
