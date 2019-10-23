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
}

PartnerImStatusIcon.template = 'mail.component.PartnerImStatusIcon';

return PartnerImStatusIcon;

});
