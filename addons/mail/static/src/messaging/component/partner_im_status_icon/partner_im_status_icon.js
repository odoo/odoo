odoo.define('mail.messaging.component.PartnerImStatusIcon', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class PartnerImStatusIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                partner: this.env.entities.Partner.get(props.partnerLocalId),
                partnerRoot: this.env.messaging.partnerRoot,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Partner}
     */
    get partner() {
        return this.env.entities.Partner.get(this.props.partnerLocalId);
    }

}

Object.assign(PartnerImStatusIcon, {
    props: {
        partnerLocalId: String,
    },
    template: 'mail.messaging.component.PartnerImStatusIcon',
});

return PartnerImStatusIcon;

});
