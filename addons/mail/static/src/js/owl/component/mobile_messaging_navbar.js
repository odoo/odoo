odoo.define('mail.component.MobileMessagingNavbar', function () {
'use strict';

class MobileMessagingNavbar extends owl.Component {
    /**
     * @param  {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = owl.useState({
            targetTabId: null,
            targetTabCounter: 0,
        });

        this._onClickCaptureGlobalEventListener = ev => this._onClickCaptureGlobal(ev);
    }

    mounted() {
        document.addEventListener('click', this._onClickCaptureGlobalEventListener, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobalEventListener, true);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const tabId = ev.currentTarget.dataset.tabId;
        this.state.targetTabId = tabId;
        this.state.targetTabCounter++;
        this.trigger('o-select-mobile-messaging-navbar-tab', {
            tabId,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (!ev.target.closest(`[data-id="${this.id}"]`)) {
            return;
        }
        if (ev.target.dataset.tabId === this.props.activeTabId) {
            return;
        }
        this.state.targetTabId = null;
        this.state.targetTabCounter++;
    }
}

MobileMessagingNavbar.defaultProps = {
    tabs: [],
};

MobileMessagingNavbar.props = {
    activeTabId: String,
    tabs: {
        type: Array,
        element: {
            type: Object,
            shape: {
                icon: {
                    type: String,
                    optional: true,
                },
                id: String,
                label: String,
            },
        },
    },
};

MobileMessagingNavbar.template = 'mail.component.MobileMessagingNavbar';

return MobileMessagingNavbar;

});
