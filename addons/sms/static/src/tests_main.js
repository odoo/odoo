/** @odoo-module **/

import { populateRegistriesFunctions } from '@mail/tests_main';

import { populateRegistries } from '@sms/model/populate_registries';

populateRegistriesFunctions.push(populateRegistries);
