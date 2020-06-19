odoo.define('web.model', function () {
    "use strict";

    const { Component, core } = owl;
    const { EventBus, Observer } = core;

    // TODO: remove this if made available in owl.utils
    function partitionBy(arr, fn) {
        let lastGroup = false;
        let lastValue;
        return arr.reduce((acc, cur) => {
            let curVal = fn(cur);
            if (lastGroup) {
                if (curVal === lastValue) {
                    lastGroup.push(cur);
                }
                else {
                    lastGroup = false;
                }
            }
            if (!lastGroup) {
                lastGroup = [cur];
                acc.push(lastGroup);
            }
            lastValue = curVal;
            return acc;
        }, []);
    }

    /**
     * Model
     *
     * The purpose of the class Model and the associated hook useModel
     * is to offer something similar to an owl store but with no automatic
     * notification (and rendering) of components when the 'state' used in the model
     * would change. Instead, one should call the __notifyComponents function whenever
     * it is useful to alert registered component. Nevertheless,
     * when calling a method throught the dispatch method, a notifcation
     * does take place automatically, and registered components (via useModel) are rendered.
     *
     * it is highly expected that this class will change in a near future. We don't have
     * the necessary hindsight to be sure its actual form is good.
     * @extends EventBus
     */
    class Model extends EventBus {

        constructor() {
            super();
            this.rev = 1;
            this.mapping = {}; // could be a weak map
        }

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * Call the base model method with given name with the arguments
         * determined by the dispatch extra arguments.
         *
         * @param {string} action
         * @param {...any} args
         * @returns {Promise<any>}
         */
        async dispatch(action, ...args) {
            const result = await this[action](...args);
            // TODO try to put it in promise.resolve()
            this._dispatch(...arguments);
            let rev = this.rev;
            await Promise.resolve();
            if (rev === this.rev) {
                await this._notifyComponents();
            }
            return result;
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {string} action
         * @param {...any} args
         */
        _dispatch(action, ...args) { }

        /**
         * see Context method in owl.js for explanation
         * @private
         */
        async _notifyComponents() {
            const rev = ++this.rev;
            const subscriptions = this.subscriptions.update;
            const groups = partitionBy(subscriptions, s => (s.owner ? s.owner.__owl__.depth : -1));
            for (let group of groups) {
                const proms = group.map(sub => sub.callback.call(sub.owner, rev));
                Component.scheduler.flush();
                await Promise.all(proms);
            }
        }
    }

    /**
     * This is more or less the hook 'useContextWithCB' from owl only slightly simplified.
     *
     * @param {string} modelName
     */
    function useModel(modelName) {
        const component = Component.current;
        const model = component.env[modelName];
        if (!(model instanceof Model)) {
            throw new Error(`No Model found when connecting '${component.constructor.name}'`);
        }

        const mapping = model.mapping;
        const __owl__ = component.__owl__;
        const componentId = __owl__.id;
        if (!__owl__.observer) {
            __owl__.observer = new Observer();
            __owl__.observer.notifyCB = component.render.bind(component);
        }
        const currentCB = __owl__.observer.notifyCB;
        __owl__.observer.notifyCB = function () {
            if (model.rev > mapping[componentId]) {
                return;
            }
            currentCB();
        };
        mapping[componentId] = 0;
        const renderFn = __owl__.renderFn;
        __owl__.renderFn = function (comp, params) {
            mapping[componentId] = model.rev;
            return renderFn(comp, params);
        };

        model.on('update', component, async modelRev => {
            if (mapping[componentId] < modelRev) {
                mapping[componentId] = modelRev;
                await component.render();
            }
        });

        const __destroy = component.__destroy;
        component.__destroy = parent => {
            model.off("update", component);
            __destroy.call(component, parent);
        };

        return model;
    }

    return {
        Model,
        useModel,
    };
});
