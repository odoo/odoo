/** @odoo-module **/

const { Component } = owl;

const { useRef } = owl.hooks;

class PartnerListing extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this._nameInputRef = useRef('name-input');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    async renameGroupChat(name) {
        this.thread.renameForAll(name);
    }

    /**
     * @returns {mail.thread_view}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _close() {
        this.trigger('o-popover-close');
    }

    _getThreadDefaultName() {
        let defaultName = "";
        for (let i = 0; i < this.thread.members.length; i++) {
            if (i !== 0) {
                defaultName += ", " + this.thread.members[i].name;
            } else {
                defaultName = this.thread.members[i].name;
            }
        }
        return defaultName;
    }

    _onKeyUp(ev) {
        if (ev.key === "Enter") {
            if (this._nameInputRef.el.value === "") {
                this.renameGroupChat(this._getThreadDefaultName())
            }
            else {
                this.renameGroupChat(this._nameInputRef.el.value)
            }
            this._close();
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------


}

Object.assign(PartnerListing, {
    props: {
        members: {
            type: Object,
        },
        threadLocalId: {
            type: String,
        }
    },
    template: 'mail.PartnerListing',
});

export default PartnerListing;
