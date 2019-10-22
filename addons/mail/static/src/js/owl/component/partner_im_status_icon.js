odoo.define('mail.component.PartnerImStatusIcon', function () {
'use strict';

class PartnerImStatusIcon extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeProps = owl.hooks.useStore((state, props) => {
            return {
                partner: state.partners[props.partnerLocalId],
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    statusClass() {
        switch (this.storeProps.partner.im_status) {
            case 'online':
                return 'text-primary';
            case 'away':
                return 'text-warning';
            case 'offline':
                return 'text-500';
            default:
                return 'text-500';
        }
    }

    statusTitle() {
        return _.str.sprintf(this._getStatusTitle(), _.escape(this.storeProps.partner.name));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getStatusTitle() {
        switch (this.storeProps.partner.im_status) {
            case 'online':
                return this.env._t("%s is online");
            case 'away':
                return this.env._t("%s is idle");
            case 'offline':
                return this.env._t("%s is offline");
            default:
                return this.env._t("The status of %s is unknown");
        }
    }

}

PartnerImStatusIcon.template = 'mail.component.PartnerImStatusIcon';

return PartnerImStatusIcon;

});
