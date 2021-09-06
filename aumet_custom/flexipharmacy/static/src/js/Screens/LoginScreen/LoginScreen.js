odoo.define('flexipharmacy.LoginScreen', function (require) {
    'use strict';

    const LoginScreen = require('pos_hr.LoginScreen');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const rentalUseSelectEmployee = require('flexipharmacy.useSelectEmployee');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    const AsplRetLoginScreenInh = (LoginScreen) =>
        class extends LoginScreen {
        constructor() {
            super(...arguments);
            this.barcodeCashierAction = this._barcodeCashierAction;
            const { selectEmployee, askPin } = rentalUseSelectEmployee();
            this.selectEmployee = selectEmployee;
            this.askPin = askPin;
        }
        async _barcodeCashierAction(code) {
            if (code && code.rfid){
                let theEmployee;
                for (let employee of this.env.pos.employees) {
                    if (employee.barcode === Sha1.hash(code.code)) {
                        theEmployee = employee;
                        break;
                    }else if(employee.rfid_pin === code.code){
                        theEmployee = employee;
                        break;
                    }
                }
                if (!theEmployee) return;
                if (theEmployee && code.rfid){
                    theEmployee['rfid'] = true
                }
                if (!theEmployee.pin || (await this.askPin(theEmployee))) {
                    this.env.pos.set_cashier(theEmployee);
                    this.back();
                }
            }else{
                super._barcodeCashierAction(code)
            }
        }
    }
    
    Registries.Component.extend(LoginScreen, AsplRetLoginScreenInh);

    return LoginScreen;
});
