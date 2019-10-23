odoo.define('mail.component.PartnerImStatusIcon', function () {
'use strict';

const { Component } = owl;
const { useStore } = owl.hooks;

class PartnerImStatusIcon extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeProps = useStore((state, props) => {
            return {
                partner: state.partners[props.partnerLocalId],
            };
        });
    }
}

PartnerImStatusIcon.template = 'mail.component.PartnerImStatusIcon';

return PartnerImStatusIcon;

});
