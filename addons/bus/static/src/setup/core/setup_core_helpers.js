/** @odoo-module **/

import { registry } from '@web/core/registry';

import { imStatusService } from '@bus/im_status_service';
import { multiTabService } from '@bus/multi_tab_service';
import { busService } from '@bus/services/bus_service';
import { presenceService } from '@bus/services/presence_service';
import { makeBusServiceToLegacyEnv } from '@bus/services/legacy/make_bus_service_to_legacy_env';

export function setupCoreBus() {
    registry.category('services')
        .add('im_status', imStatusService)
        .add('multi_tab', multiTabService)
        .add('bus_service', busService)
        .add('presence', presenceService);
    registry.category('wowlToLegacyServiceMappers')
        .add('bus_service_to_legacy_env', makeBusServiceToLegacyEnv);
}
