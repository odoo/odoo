odoo.define('mail.messaging.component.PopoverButtonWithComponent', function (require) {
'use strict';

const components = {
    PopoverButton: require('mail.messaging.component.PopoverButton'),
};

/**
 * Popover button variant which (un)mount a given component as popover content.
 */
class PopoverButtonWithComponent extends components.PopoverButton {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        /**
         * Node reference of the popover component.
         */
        this._popoverComponent = undefined;
    }

    /**
     * Create and mount the popover component in a virtual node in prevision
     * for it to be printed in the popover.
     *
     * @override
     */
    async mounted() {
        await super.mounted();
        this._popoverComponent = this._createPopoverComponent();
        await this._popoverComponent.mount(document.createElement('div'));
        if (this.__owl__.isDestroyed) {
            return;
        }
        this._popoverComponent.el.outerHTML = this._popoverComponent.el;
    }

    /**
     * Unmount and destroy the component.
     *
     * @override
     */
    willUnmount() {
        super.willUnmount();
        this._popoverComponent.__owl__.isMounted = false;
        this._popoverComponent.destroy();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * To be overriden by sub components
     *
     * @private
     */
    _createPopoverComponent() {}

    /**
     * Use the component content as the popover content.
     *
     * @private
     */
    _getPopoverContent() {
        this._popoverComponent.__owl__.isMounted = true;
        return this._popoverComponent.el;
    }

}

return PopoverButtonWithComponent;

});
