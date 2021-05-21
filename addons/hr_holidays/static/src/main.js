/** @odoo-module **/

import '@mail/main';

import { populateRegistries } from '@hr_holidays/model/populate_registries';

import env from 'web.commonEnv';

populateRegistries({ env });
