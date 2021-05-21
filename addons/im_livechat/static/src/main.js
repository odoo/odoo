/** @odoo-module **/

import '@mail/main';

import { populateRegistries } from '@im_livechat/model/populate_registries';

import env from 'web.commonEnv';

populateRegistries({ env });
