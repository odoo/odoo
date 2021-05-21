/** @odoo-module **/

import '@mail/main';

import { populateRegistries } from '@sms/model/populate_registries';

import env from 'web.commonEnv';

populateRegistries({ env });
