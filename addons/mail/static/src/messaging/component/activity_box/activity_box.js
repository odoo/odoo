odoo.define('mail.messaging.component.ActivityBox', function (require) {
'use strict';

const components = {
    Activity: require('mail.messaging.component.Activity'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class ActivityBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatter = this.env.entities.Chatter.get(props.chatterLocalId);
            return {
                chatter,
                futureActivitiesCount: chatter ? chatter.futureActivities.length : 0,
                overdueActivitiesCount: chatter ? chatter.overdueActivities.length : 0,
                todayActivitiesCount: chatter ? chatter.todayActivities.length : 0,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Chatter}
     */
    get chatter() {
        return this.env.entities.Chatter.get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickTitle() {
        this.chatter.toggleActivityBoxVisibility();
    }

}

Object.assign(ActivityBox, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.messaging.component.ActivityBox',
});

return ActivityBox;

});
