odoo.define('mail/static/src/components/chatter_container/chatter_container.js', function (require) {
'use strict';

const components = {
    Chatter: require('mail/static/src/components/chatter/chatter.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

/**
 * This component abstracts chatter component to its parent, so that it can be
 * mounted and receive chatter data even when a chatter component cannot be
 * created. Indeed, in order to create a chatter component, we must create
 * a chatter record, the latter requiring messaging to be initialized. The view
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
                this.chatter = this.env.models['mail.chatter'].create(props);
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
     * chatter record as its data.
     */
    template: 'mail.ChatterContainer',
});


return ChatterContainer;

});
