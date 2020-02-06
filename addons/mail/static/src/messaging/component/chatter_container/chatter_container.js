odoo.define('mail.messaging.component.ChatterContainer', function (require) {
'use strict';

const components = {
    Chatter: require('mail.messaging.component.Chatter'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

/**
 * This component abstracts chatter component to its parent, so that it can be
 * mounted and receive chatter data even when a chatter component cannot be
 * created. Indeed, in order to create a chatter component, we must create
 * a chatter entity, the latter requiring messaging to be initialized. The view
 * may attempt to create a chatter before messaging has been initialized, so
 * this component delays the mounting of chatter until it becomes initialized.
 */
class ChatterContainer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.chatter = undefined;
        this._wasMessagingInitialized = false;
        useStore(props => {
            const isMessagingInitialized = this.env.isMessagingInitialized();
            if (!this._wasMessagingInitialized && isMessagingInitialized) {
                this._wasMessagingInitialized = true;
                this.chatter = this.env.entities.Chatter.create(props);
            }
            return { isMessagingInitialized };
        });
    }

    mounted() {
        this._update();
    }

    patched() {
        this._update();
    }

    destroy() {
        super.destroy();
        if (this.chatter) {
            this.chatter.delete();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (this.chatter) {
            this.chatter.update(this.props);
        }
    }

}

Object.assign(ChatterContainer, {
    components,
    /**
     * No props validation because this component simply forwards props to
     * chatter entity as its data.
     */
    template: 'mail.messaging.component.ChatterContainer',
});


return ChatterContainer;

});
