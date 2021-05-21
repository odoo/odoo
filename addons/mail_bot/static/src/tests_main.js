/** @odoo-module **/

import { populateRegistriesFunctions } from '@mail/tests_main';

import { populateRegistries } from '@mail_bot/model/populate_registries';

populateRegistriesFunctions.push(populateRegistries);
