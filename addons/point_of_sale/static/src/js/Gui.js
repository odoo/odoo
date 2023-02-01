/** @odoo-module */
const { status } = owl;

const config = {};
/**
 * Call this when the user interface is ready. Provide the component
 * that will be used to control the ui.
 * @param {component} component component having the ui methods.
 */
export const configureGui = ({ component }) => {
    config.component = component;
    config.availableMethods = new Set(["setSyncStatus"]);
};

export class GuiNotReadyError extends Error {}
// FIXME POSREF: remove this entirely.
export const Gui = new Proxy(config, {
    get(target, key) {
        const { component, availableMethods } = target;
        if (!component) {
            throw new Error(`Call 'configureGui' before using Gui.`);
        }
        const isMounted = status(component) === "mounted";
        if (availableMethods.has(key) && isMounted) {
            return component[key].bind(component);
        }
        throw new GuiNotReadyError(`Attempted get ${key} on Gui when Chrome is not yet mounted.`);
    },
});
