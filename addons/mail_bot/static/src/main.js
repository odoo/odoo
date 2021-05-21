/** @odoo-module **/

import '@mail/main';

import { populateRegistries } from '@mail_bot/model/populate_registries';

import env from 'web.commonEnv';

populateRegistries({ env });
