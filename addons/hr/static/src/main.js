/** @odoo-module **/

import { factoryEmployee } from '@hr/models/employee/employee';

import '@mail/js/main';
import { registerNewModel } from '@mail/model/model_core';

import env from 'web.commonEnv';

registerNewModel('hr.employee', factoryEmployee);
env.modelManager.modelRegistry.set('hr.employee', factoryEmployee);
