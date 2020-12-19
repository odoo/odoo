odoo.define('mail_media_repository/static/src/components/media_select_button/media_select_button.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useState, useRef } = owl.hooks;

const components = {
    Dialog: require('web.OwlDialog'),
};

class MediaSelectButton extends Component {

    constructor(...args) {
        super(...args);

        this.repository = undefined;
        this._wasMessagingInitialized = false;
        useStore(props => {
            // Delay creation of chatter record until messaging is initialized.
            // Ideally should observe models directly to detect change instead
            // of using `useStore`.
            if (!this._wasMessagingInitialized) {
                this._wasMessagingInitialized = true;
                this._insertFromProps(props);
            }
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                repository: this.repository ? this.repository.__state : undefined,
                thread: thread ? thread.__state : undefined,
            };
        });

        this.state = useState({
            hasMediaSelectDialog: false,
        });
    }

    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    /**
     * @returns {string|undefined}
     */
    get TITLE() {
        return this.env._t("Select Media to Send");
    }

    mounted() {
        this._update();
    }

    patched() {
        this._update();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _insertFromProps(props) {
        const values = Object.assign({}, props);
        if (!this.repository) {
            this.repository = this.env.models['mail_media_repository.attachment'].create(values);
        } else {
            this.repository.update(values);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------
    /**
     * Called when clicking on attachment button.
     *
     * @private
     */
    _onClickSelectMedia(ev) {
        ev.preventDefault();
        this.state.hasMediaSelectDialog = true;
        this.repository.performRpcMediaFetch(30, 0);
    }

    _onMediaClick(media) {
        this.thread.composer.postMessageWithMedia(media);
    }

    /**
     * @private
     */
    _onDialogOK() {
        this.state.hasMediaSelectDialog = false;
    }

    _onDialogCancel() {
        this.state.hasMediaSelectDialog = false;
    }
}

Object.assign(MediaSelectButton, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail_media_repository.MediaSelectButton',
});

return MediaSelectButton;

});
