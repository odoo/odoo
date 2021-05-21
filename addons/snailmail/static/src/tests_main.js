/** @odoo-module **/

import { populateRegistriesFunctions } from '@mail/tests_main';

import { populateRegistries } from '@snailmail/model/populate_registries';

populateRegistriesFunctions.push(populateRegistries);
