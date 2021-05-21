/** @odoo-module **/

import { factoryVisitor } from '@website_livechat/models/visitor/visitor';

import '@mail/js/main';
import { registerNewModel } from '@mail/model/model_core';

import env from 'web.commonEnv';

registerNewModel('website_livechat.visitor', factoryVisitor);
env.modelManager.modelRegistry.set('website_livechat.visitor', factoryVisitor);
