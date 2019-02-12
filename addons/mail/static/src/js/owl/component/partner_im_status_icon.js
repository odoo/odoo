odoo.define('mail.component.PartnerImStatusIcon', function () {
'use strict';

class PartnerImStatusIcon extends owl.store.ConnectedComponent {}

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.partnerLocalId
 * @return {Object}
 */
PartnerImStatusIcon.mapStoreToProps = function (state, ownProps) {
    return {
        partner: state.partners[ownProps.partnerLocalId],
    };
};

PartnerImStatusIcon.template = 'mail.component.PartnerImStatusIcon';

return PartnerImStatusIcon;

});
