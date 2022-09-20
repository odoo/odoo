/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { makeDeferred } from '@mail/utils/deferred';

import { browser } from '@web/core/browser/browser';

const { EventBus } = owl;

registerModel({
    name: 'Messaging',
    lifecycleHooks: {
        _created() {
            odoo.__DEBUG__.messaging = this;
        },
        _willDelete() {
            delete odoo.__DEBUG__.messaging;
        },
    },
    recordMethods: {
        /**
         * Perform a rpc call and return a promise resolving to the result.
         *
         * @param {Object} params
         * @return {any}
         */
        async rpc(params, options = {}) {
            if (params.route) {
                const { route, params: rpcParameters } = params;
                const { shadow: silent, ...rpcSettings } = options;
                return this.env.services.rpc(route, rpcParameters, { silent, ...rpcSettings });
            } else {
                const { args, method, model, kwargs = {} } = params;
                const { domain, fields, groupBy } = kwargs;

                const ormService = 'shadow' in options ? this.env.services.orm.silent : this.env.services.orm;
                switch (method) {
                    case 'create':
                        return ormService.create(model, args[0], kwargs);
                    case 'read':
                        return ormService.read(model, args[0], args.length > 1 ? args[1] : undefined, kwargs);
                    case 'read_group':
                        return ormService.readGroup(model, domain, fields, groupBy, kwargs);
                    case 'search':
                        return ormService.search(model, args[0], kwargs);
                    case 'search_read':
                        return ormService.searchRead(model, domain, fields, kwargs);
                    case 'unlink':
                        return ormService.unlink(model, args[0], kwargs);
                    case 'write':
                        return ormService.write(model, args[0], args[1], kwargs);
                    default:
                        return ormService.call(model, method, args, kwargs);
                }
            }
        },
        /**
         * Starts messaging and related records.
         */
        async start() {
            this.update({ isInitialized: true });
            this.initializedPromise.resolve();
        },
    },
    fields: {
        /**
         * Inverse of the messaging field present on all models. This field
         * therefore contains all existing records.
         */
        allRecords: many('Record', {
            inverse: 'messaging',
            isCausal: true,
        }),
        browser: attr({
            compute() {
                return browser;
            },
        }),
        device: one('Device', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        /**
         * Promise that will be resolved when messaging is initialized.
         */
        initializedPromise: attr({
            compute() {
                return makeDeferred();
            },
            required: true,
        }),
        isInitialized: attr({
            default: false,
        }),
        locale: one('Locale', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines the bus that is used to communicate messaging events.
         */
        messagingBus: attr({
            compute() {
                if (this.messagingBus) {
                    return; // avoid overwrite if already provided (example in tests)
                }
                return new EventBus();
            },
            required: true,
        }),
    },
});
