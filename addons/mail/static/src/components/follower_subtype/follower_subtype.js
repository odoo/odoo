odoo.define('mail/static/src/components/follower_subtype/follower_subtype.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class FollowerSubtype extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.follower|undefined}
     */
    get follower() {
        return this.env.models['mail.follower'].get(this.props.followerLocalId);
    }

    /**
     * @returns {mail.follower_subtype}
     */
    get followerSubtype() {
        return this.env.models['mail.follower_subtype'].get(this.props.followerSubtypeLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on cancel button.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeCheckbox(ev) {
        if (ev.target.checked) {
            this.follower.selectSubtype(this.followerSubtype);
        } else {
            this.follower.unselectSubtype(this.followerSubtype);
        }
    }

}

Object.assign(FollowerSubtype, {
    props: {
        followerLocalId: String,
        followerSubtypeLocalId: String,
    },
    template: 'mail.FollowerSubtype',
});

return FollowerSubtype;

});
