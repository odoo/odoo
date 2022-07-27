/** @odoo-module */

import { useModels } from "@mail/component_hooks/use_models/use_models";
import { useShouldUpdateBasedOnProps } from "@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props";

const componentRegistry = {};

/**
 * Allows a component to lean on the messaging features: the component is
 * subscribed to changes in messaging models in its environment, the component
 * will only be rerenderd if its props change, and the component has access to
 * all components that are registered with this function without having to
 * explicitly import them.
 *
 * @param {Component} ComponentClass the constructor of the component to be
 *      registered. Its name will be used as its key in the registry.
 * @param {Object} [param1]
 * @param {Object} [param1.propsCompareDepth] @see useShouldUpdateBasedOnProps
 */
export function registerMessagingComponent(ComponentClass, { propsCompareDepth = {} } = {}) {
    const { name, components } = ComponentClass;
    if (componentRegistry[name]) {
        throw new Error(`There already is a registered component with the name "${name}"`);
    }
    const decoratedName = `@messaging ${name}`;
    // Defining the class in an object and immediately taking it out so that it
    // has "decoratedName" as its class name in stack traces and stuff.
    const MessagingClass = { [decoratedName]: class extends ComponentClass {
        setup(...args) {
            super.setup(...args);
            // useModels must be defined after useRenderedValues, indeed records and
            // fields accessed during useRenderedValues should be observed by
            // useModels as if they were part of the OWL rendering itself.
            useModels();
            useShouldUpdateBasedOnProps({ propsCompareDepth });
        }
        get messaging() {
            return this.env.services.messaging.modelManager.messaging;
        }
        /**
         * @returns {string}
         */
        toString() {
            return `component(${decoratedName}, props: ${Object.entries(this.props || {})})`;
        }
    } }[decoratedName];
    // Create an object whose prototype is the component registry with the values of the original
    // Component.components. This means that trying to get a value from this object will first look
    // into the original Component's components, and fall back on the registry if not found.
    MessagingClass.components = Object.assign(Object.create(componentRegistry), components);
    componentRegistry[name] = MessagingClass;
}

/**
 * Unregisters a component from the registry. The component will not be
 * unpatched as the main purpose of this method is to clean up the registry
 * when using one-off components in tests.
 *
 * @param {function} ComponentClass the constructor of the component to be
 *      unregistered. Its name will be used as its key in the registry.
 */
export function unregisterMessagingComponent(ComponentClass) {
    delete componentRegistry[ComponentClass.name];
}

/**
 * Returns the currently registered component in the registry for a given name.
 *
 * @param {string} name the class name of the component to get
 * @returns {Component} the decorated component
 */
export function getMessagingComponent(name) {
    return componentRegistry[name];
}
