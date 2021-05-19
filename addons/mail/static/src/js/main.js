/** @odoo-module **/

import { compute } from '@mail/model/fields/properties/compute/compute';
import { defaultProperty } from '@mail/model/fields/properties/default/default';
import { dependencies } from '@mail/model/fields/properties/dependencies/dependencies';
import { fieldName } from '@mail/model/fields/properties/field_name/field_name';
import { inverse } from '@mail/model/fields/properties/inverse/inverse';
import { isCausal } from '@mail/model/fields/properties/is_causal/is_causal';
import { isMany2X } from '@mail/model/fields/properties/is_many2x/is_many2x';
import { isOnChange } from '@mail/model/fields/properties/is_on_change/is_on_change';
import { isOne2X } from '@mail/model/fields/properties/is_one2x/is_one2x';
import { isRelation } from '@mail/model/fields/properties/is_relation/is_relation';
import { isX2Many } from '@mail/model/fields/properties/is_x2many/is_x2many';
import { isX2One } from '@mail/model/fields/properties/is_x2one/is_x2one';
import { readonly } from '@mail/model/fields/properties/readonly/readonly';
import { related } from '@mail/model/fields/properties/related/related';
import { required } from '@mail/model/fields/properties/required/required';
import { to } from '@mail/model/fields/properties/to/to';
import { attribute } from '@mail/model/fields/types/attribute/attribute';
import { relation } from '@mail/model/fields/types/relation/relation';
import ModelManager from '@mail/model/model_manager';
import MessagingService from '@mail/services/messaging/messaging';

import env from 'web.commonEnv';
import { serviceRegistry } from 'web.core';

const { Store } = owl;
const { EventBus } = owl.core;

async function createMessaging() {
    await new Promise(resolve => {
        /**
         * Called when all JS resources are loaded. This is useful in order
         * to do some processing after other JS files have been parsed, for
         * example new models or patched models that are coming from
         * other modules, because some of those patches might need to be
         * applied before messaging initialization.
         */
        window.addEventListener('load', resolve);
    });
    /**
     * All JS resources are loaded, but not necessarily processed.
     * We assume no messaging-related modules return any Promise,
     * therefore they should be processed *at most* asynchronously at
     * "Promise time".
     */
    await new Promise(resolve => setTimeout(resolve));
    /**
     * Some models require session data, like locale text direction (depends on
     * fully loaded translation).
     */
    await env.session.is_bound;

    env.modelManager.start();
    /**
     * Create the messaging singleton record.
     */
    env.messaging = env.models['mail.messaging'].create();
}

/**
 * Messaging store
 */
const store = new Store({
    env,
    state: {
        messagingRevNumber: 0,
    },
});

/**
 * Registry of models.
 */
env.models = {};
const fieldPropertyRegistry = new Map([
    ['compute', compute],
    ['default', defaultProperty],
    ['dependencies', dependencies],
    ['fieldName', fieldName],
    ['inverse', inverse],
    ['isCausal', isCausal],
    ['isMany2X', isMany2X],
    ['isOnChange', isOnChange],
    ['isOne2X', isOne2X],
    ['isRelation', isRelation],
    ['isX2Many', isX2Many],
    ['isX2One', isX2One],
    ['readonly', readonly],
    ['related', related],
    ['required', required],
    ['to', to],
]);
const fieldTypeRegistry = new Map([
    ['attribute', attribute],
    ['relation', relation],
]);
/**
 * Environment keys used in messaging.
 */
Object.assign(env, {
    autofetchPartnerImStatus: true,
    destroyMessaging() {
        if (env.modelManager) {
            env.modelManager.deleteAll();
            env.messaging = undefined;
        }
    },
    disableAnimation: false,
    isMessagingInitialized() {
        if (!this.messaging) {
            return false;
        }
        return this.messaging.isInitialized;
    },
    /**
     * States whether the environment is in QUnit test or not.
     *
     * Useful to prevent some behaviour in QUnit tests, like applying
     * style of attachment that uses url.
     */
    isQUnitTest: false,
    loadingBaseDelayDuration: 400,
    messaging: undefined,
    messagingBus: new EventBus(),
    /**
     * Promise which becomes resolved when messaging is created.
     *
     * Useful for discuss widget to know when messaging is created, because this
     * is an essential condition to make it work.
     */
    messagingCreatedPromise: createMessaging(),
    modelManager: new ModelManager({ env, fieldPropertyRegistry, fieldTypeRegistry }),
    store,
});

/**
 * Components cannot use web.bus, because they cannot use
 * EventDispatcherMixin, and webclient cannot easily access env.
 * Communication between webclient and components by core.bus
 * (usable by webclient) and messagingBus (usable by components), which
 * the messaging service acts as mediator since it can easily use both
 * kinds of buses.
 */
env.bus.on(
    'hide_home_menu',
    null,
    () => env.messagingBus.trigger('hide_home_menu')
);
env.bus.on(
    'show_home_menu',
    null,
    () => env.messagingBus.trigger('show_home_menu')
);
env.bus.on(
    'will_hide_home_menu',
    null,
    () => env.messagingBus.trigger('will_hide_home_menu')
);
env.bus.on(
    'will_show_home_menu',
    null,
    () => env.messagingBus.trigger('will_show_home_menu')
);

serviceRegistry.add('messaging', MessagingService);
