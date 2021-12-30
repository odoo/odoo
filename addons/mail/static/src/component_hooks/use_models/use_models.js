/** @odoo-module **/

import { Listener } from '@mail/model/model_listener';
import { followRelations } from '@mail/model/model_utils';

const { onMounted, onPatched, useComponent } = owl.hooks;

/**
 * This hook provides support for automatically re-rendering when used records
 * or fields changed.
 *
 * Components that use this hook must be instantiated after messaging service is
 * started. However there is no restriction on the messaging record (coming from
 * the modelManager of the messaging service) being already initialized or even
 * created.
 *
 * @param {Object} [param={}]
 * @param {string[]} [param.extraCacheList=[]]
 * @param {string} [param.modelName]
 * @param {string} [param.propNameAsRecordLocalId]
 * @param {string} [param.recordName]
 */
export function useModels({ extraCacheList = [], modelName, propNameAsRecordLocalId, recordName } = {}) {
    const component = useComponent();
    const { modelManager } = component.env.services.messaging;
    const { messaging } = modelManager;
    component.messaging = messaging && messaging.getImmutable();
    const listener = new Listener({
        isLocking: false, // unfortunately __render has side effects such as children components updating their reference to their corresponding model
        name: `useModels() of ${component}`,
        onChange: () => component.render(),
    });
    const __render = component.__render;
    let lastRenderedMessaging;
    let lastRenderedRecord;
    let lastPatchedMessaging;
    let lastPatchedRecord;
    component.__render = fiber => {
        if (modelManager) {
            modelManager.startListening(listener);
            // last rendered messaging
            const { messaging } = modelManager;
            lastRenderedMessaging = messaging && messaging.getImmutable();
            component.messaging = lastRenderedMessaging;
            // last rendered record
            if (modelName && propNameAsRecordLocalId && recordName) {
                lastRenderedRecord = modelManager.models[modelName].getImmutable(component.props[propNameAsRecordLocalId]);
                component[recordName] = lastRenderedRecord;
            }
            // extra cache list
            if (component.messaging) { // messaging is sometimes undefined, example when first creating root components
                for (const extraCache of extraCacheList) {
                    const [getterName, ...relatedPath] = extraCache.split('.');
                    followRelations(component[getterName], relatedPath.join('.'));
                }
            }
        }
        __render.call(component, fiber);
        if (modelManager) {
            modelManager.stopListening(listener);
        }
        component.messaging = lastPatchedMessaging;
        if (modelName && propNameAsRecordLocalId && recordName) {
            component[recordName] = lastPatchedRecord;
        }
    };
    onMounted(onUpdate);
    onPatched(onUpdate);
    function onUpdate() {
        // last patched messaging
        lastPatchedMessaging = lastRenderedMessaging;
        component.messaging = lastPatchedMessaging;
        // last patched record
        if (modelName && propNameAsRecordLocalId && recordName) {
            lastPatchedRecord = lastRenderedRecord;
            component[recordName] = lastPatchedRecord;
        }
    }
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        if (modelManager) {
            modelManager.removeListener(listener);
        }
        if (modelName && propNameAsRecordLocalId && recordName) {
            component[recordName] = undefined;
        }
        component.messaging = undefined;
        __destroy.call(component, parent);
    };
    modelManager.messagingCreatedPromise.then(() => {
        component.render();
    });
}
