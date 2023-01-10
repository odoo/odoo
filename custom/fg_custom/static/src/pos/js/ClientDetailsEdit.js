odoo.define('fg_custom.FgClientDetailsEdit', function(require) {
    'use strict';

    const { _t } = require('web.core');
    const { getDataURLFromFile } = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');

    const FgClientDetailsEdit = ClientDetailsEdit =>
        class extends ClientDetailsEdit {
            /**
             * @override
             */
            saveChanges() {
                let processedChanges = {};
                for (let [key, value] of Object.entries(this.changes)) {
                    if (this.intFields.includes(key)) {
                        processedChanges[key] = parseInt(value) || false;
                    } else {
                        processedChanges[key] = value;
                    }
                }
                if ((!this.props.partner.x_pwd_id && !processedChanges.x_pwd_id) || processedChanges.x_pwd_id === ''){
                    return this.showPopup('ErrorPopup', {
                      title: _t('A Customer PWD ID Is Required'),
                    });
                }else if((!this.props.partner.x_senior_id && !processedChanges.x_senior_id) || processedChanges.x_senior_id === ''){
                    return this.showPopup('ErrorPopup', {
                      title: _t('A Customer Senior ID Is Required'),
                    });
                }else{
                    super.saveChanges();
                }
            }
        };

    Registries.Component.extend(ClientDetailsEdit, FgClientDetailsEdit);

    return FgClientDetailsEdit;
});
