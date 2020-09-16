odoo.define('mail/static/src/components/follower_subtype_list/follower_subtype_list.js', function (require) {
'use strict';

const components = {
    FollowerSubtype: require('mail/static/src/components/follower_subtype/follower_subtype.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component, QWeb } = owl;

class FollowerSubtypeList extends Component {

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
     * @returns {mail.follower_subtype_list}
     */
    get followerSubtypeList() {
        return this.env.models['mail.follower_subtype_list'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on cancel button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCancel(ev) {
        this.followerSubtypeList.__mfield_follower(this).closeSubtypes();
    }

    /**
     * Called when clicking on apply button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickApply(ev) {
        this.followerSubtypeList.__mfield_follower(this).updateSubtypes();
    }

}

Object.assign(FollowerSubtypeList, {
    components,
    props: {
        localId: String,
    },
    template: 'mail.FollowerSubtypeList',
});

QWeb.registerComponent('FollowerSubtypeList', FollowerSubtypeList);

return FollowerSubtypeList;

});
