odoo.define('point_of_sale.Gui', function (require) {
    'use strict';

    /**
     * This module bridges the data classes (such as those defined in
     * models.js) to the view (owl.Component) but not vice versa.
     *
     * The idea is to be able to perform side-effects to the user interface
     * during calculation. Think of console.log during times we want to see
     * the result of calculations. This is no different, except that instead
     * of printing something in the console, we access a method in the user
     * interface then the user interface reacts, e.g. calling `showPopup`.
     *
     * This however can be dangerous to the user interface as it can be possible
     * that a rendered component is destroyed during the calculation. Because of
     * this, we are going to limit external ui controls to those safe ones to
     * use such as:
     *  - `showPopup`
     *  - `showTempScreen`
     *
     * IMPROVEMENT: After all, this Gui layer seems to be a good abstraction because
     * there is a complete decoupling between data and view despite the data being
     * able to use selected functionalities in the view layer. More formalized
     * implementation is welcome.
     */

    const config = {};

    /**
     * Call this when the user interface is ready. Provide the component
     * that will be used to control the ui.
     * @param {owl.component} component component having the ui methods.
     */
    const configureGui = ({ component }) => {
        config.component = component;
        config.availableMethods = new Set([
            'showPopup',
            'showTempScreen',
            'playSound',
            'setSyncStatus',
            'showNotification',
        ]);
    };

    /**
     * Import this and consume like so: `Gui.showPopup(<PopupName>, <props>)`.
     * Like you would call `showPopup` in a component.
     */
    const Gui = new Proxy(config, {
        get(target, key) {
            const { component, availableMethods } = target;
            if (!component) throw new Error(`Call 'configureGui' before using Gui.`);
            const isMounted = component.__owl__.status === 3 /* mounted */;
            if (availableMethods.has(key) && isMounted) {
                return component[key].bind(component);
            }
        },
    });

    return { configureGui, Gui };
});
