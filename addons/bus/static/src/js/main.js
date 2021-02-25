/** @odoo-module **/

import { crossTabCommunicationService } from '@bus/services/crosstab_communication';
import { localStorageCommunicationService } from '@bus/services/localstorage_communication';
import { longpollingCommunicationService } from '@bus/services/longpolling_communication';
import { serverCommunicationService } from '@bus/services/server_communication';
import { userPresenceService } from '@bus/services/user_presence';

import env from 'web.commonEnv';

// deployment order is important (should respect dependencies of services)
const services = [
    localStorageCommunicationService,
    crossTabCommunicationService,
    userPresenceService,
    longpollingCommunicationService,
    serverCommunicationService,
];

for (const { deploy, name } of services) {
    env.services[name] = deploy(env);
}
