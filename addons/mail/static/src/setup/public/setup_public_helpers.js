/** @odoo-module **/

import { data } from 'mail.discuss_public_channel_template';

import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { DiscussPublicViewContainer } from '@mail/components/discuss_public_view_container/discuss_public_view_container';
import { PopoverManagerContainer } from '@mail/components/popover_manager_container/popover_manager_container';
import { setupCoreMessaging } from '@mail/setup/core/setup_core_helpers';

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

import { Component, mount, whenReady } from '@odoo/owl';

Component.env = legacyEnv;

export function setupPublicMessaging() {
    setupCoreMessaging();
    registry.category('services')
        .add('legacy_rpc', makeLegacyRpcService(Component.env))
        .add('legacy_session', makeLegacySessionService(Component.env, legacySession))
        .add('legacy_notification', makeLegacyNotificationService(Component.env))
        .add('legacy_crash_manager', makeLegacyCrashManagerService(Component.env))
        .add('legacy_dialog_mapping', makeLegacyDialogMappingService(Component.env));
    registry.category('main_components')
        .add('DiscussPublicViewContainer', { Component: DiscussPublicViewContainer, props: { data } })
        // needed by the attachment viewer
        .add('DialogManagerContainer', { Component: DialogManagerContainer })
        .add('PopoverManagerContainer', { Component: PopoverManagerContainer });
}

export async function bootPublicMessaging() {
    await whenReady();
    AbstractService.prototype.deployServices(Component.env);
    setupPublicMessaging();
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
}
