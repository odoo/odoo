odoo.define('l10n_latam_pos.PartnerDetailsEdit', function (require) {
    'use strict';

    const PartnerDetailsEdit = require('point_of_sale.PartnerDetailsEdit');
    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');

    const LatamPartnerDetailsEdit = PartnerDetailsEdit =>
        class extends PartnerDetailsEdit {
        /*
        * Setup l10n_latam_identification_type_id
        */
        setup() {
            super.setup();
            this.intFields = ['country_id', 'state_id', 'property_product_pricelist', 'l10n_latam_identification_type_id'];
            const partner = this.props.partner;
            this.changes = {...this.changes, ...{
                'l10n_latam_identification_type_id': partner.l10n_latam_identification_type_id ? partner.l10n_latam_identification_type_id : this.env.pos.vat_types && this.env.pos.vat_types[0].id,
            }};
        }
        /*
        * Validate fields when create or update partner
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
            let partner_merged = {...this.props.partner, ...processedChanges};
            let validation_error = this.validatePartner(partner_merged);
            if (validation_error){
                return validation_error;
            }
            super.saveChanges();
        }
        /*
        * Show a warning about how modifying vat is not recommended
        */
        _onClickEditVat(event) {
            var self = this;
            this.showPopup('ConfirmPopup', {
                title: this.env._t('You should not change the VAT.'),
                body: this.env._t('Instead create a new client. If you have any doubt please contact with support team.'),
            }).then(({ confirmed }) => {
                if (confirmed){
                    self.trigger('create-new-client');
                }
            });
        }
        /*
        * Validate partner vat when vat input lose the focus
        */
        _onFocusOutVat(event) {
            this.verify_partner_vat(event);
        }
        /*
        * Search partners with vat param to show others with same value
        */
        verify_partner_vat(event){
            var vat = $(event.target).val();
            var customers = this.env.pos.db.search_partner(vat);
            if(vat && customers.length > 0){
                for (var i = 0; i < customers.length; i++) {
                    if(customers[i].vat === vat){
                        this.trigger('load-client', {partner: customers[i]});
                        return;
                    }
                }
            }

        }
        /*
        * Validate partner fields when partner form is saved
        */
        validatePartner(partner) {
            var fields_to_validate = [
                ['vat', 'check_vat', this.env._t('Vat'), false],
                ['email', 'check_email', this.env._t('Email'), false],
            ];
            for (var i=0; i<fields_to_validate.length; i++) {
                var field = fields_to_validate[i];
                var field_value = false;
                if(partner[field[0]]){
                    var field_value = partner[field[0]];
                }
                if(!field_value){
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Validation failed for field ') + field[2],
                        body: field[3] ? this.env._t(field[3]) : this.env._t("This field is required."),
                    });
                }
                if(field[1]){
                    var validation_result = this[field[1]](field_value, partner);
                    if(validation_result){
                        return validation_result;
                    }
                }
            }
            // No error so far
            return false;
        }
        /*
        * Validate email using aux regex
        */
        check_email(email, partner){
            if(!this.validateEmail(email)){
                return this.showPopup('ErrorPopup', {
                    'title': this.env._t("Error"),
                    'body': this.env._t("Invalid email address!"),
                });
            }
            return false;
        }
        /*
        * Validate vat. Intended to be inherited
        */
        check_vat(vat, partner){
            // No error so far
            return false;
        }
        /*
        * Aux function to validate correct email address
        */
        validateEmail(email){
            if (email){
                var RE_EMAIL = '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$';
                const emailArray = email.split(",");
                for (var y = 0; y < emailArray.length; y++) {
                    if (!emailArray[y].match(RE_EMAIL)){
                        return false;
                    }
                }
            }
            return true;
        }
    };

    Registries.Component.extend(PartnerDetailsEdit, LatamPartnerDetailsEdit);

    return PartnerDetailsEdit;
});
