/* @odoo-module */

import { useListener } from '@web/core/utils/hooks';

/**
 * Allows a component to have controls to 2 types of screens -
 * main and temporary.
 */
const ScreenControllerMixin = function (PosComponent) {
    class ScreenController extends PosComponent {
        setup() {
            super.setup();
            useListener('show-main-screen', this._onShowMainScreen);
            useListener('show-temp-screen', this._onShowTempScreen);
            useListener('close-temp-screen', this._onCloseTempScreen);
            this.mainScreen = owl.useState({
                name: null,
                props: {},
                component: null,
            });
            this.tempScreen = owl.useState({
                name: null,
                props: {},
                component: null,
                isShown: false,
            });
        }
        _onShowMainScreen(event) {
            const { name, props } = event.detail;
            this.mainScreen.name = name;
            this.mainScreen.component = this.constructor.components[name];
            this.mainScreen.props = props || {};
        }
        _onShowTempScreen(event) {
            const { name, props, resolve } = event.detail;
            const Component = this.constructor.components[name];
            if (!Component) {
                throw new Error(
                    `'${name}' is not registered as a PosComponent. Make sure to define it and register with 'Registries.Component.add'.`
                );
            }
            if (!Component.isTempScreen) {
                throw new Error(`Cannot show '${name}' as a temporary screen. Use TemporaryScreenMixin to declare it.`);
            }
            this.tempScreen.isShown = true;
            this.tempScreen.name = name;
            this.tempScreen.component = Component;
            this.tempScreen.props = Object.assign({}, props, { resolve });
        }
        _onCloseTempScreen(event) {
            this.tempScreen.props.resolve(event.detail);
            this.tempScreen.isShown = false;
            this.tempScreen.name = null;
            this.tempScreen.component = null;
            this.tempScreen.props = {};
        }
    }
    return ScreenController;
};

export default ScreenControllerMixin;
