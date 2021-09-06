odoo.define('flexipharmacy.internalTransferPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class internalTransferPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({PickingMsg: '', PickingType: '', stateOfPicking:'draft', SourceLocation:'', DestLocation:'', BlankValidationPicking: false, BlankValidationSource: false, BlankValidationDest: false});
        }
        getPayload() {
            return {stateOfPicking: this.state.stateOfPicking, SourceLocation: this.state.SourceLocation, DestLocation: this.state.DestLocation, PickingType: this.state.PickingType};
        }
        confirm(){
            if (this.state.stateOfPicking && this.state.SourceLocation && this.state.DestLocation && this.state.PickingType){
                if (this.state.SourceLocation === this.state.DestLocation){
                    this.state.PickingMsg = "Source and Destination Location is same"
                }else{
                    this.props.resolve({
                        confirmed: true, 
                        payload: {
                            stateOfPicking: this.state.stateOfPicking,
                            SourceLocation: this.state.SourceLocation, 
                            DestLocation: this.state.DestLocation, 
                            PickingType: this.state.PickingType
                        }
                    });
                }
            }else{
                this.state.BlankValidationPicking = !this.state.PickingType ? true : false;
                this.state.BlankValidationSource = !this.state.SourceLocation ? true : false;
                this.state.BlankValidationDest = !this.state.DestLocation ? true : false;
                this.state.PickingMsg = "Some Information missing"
            }
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    internalTransferPopup.template = 'internalTransferPopup';
    internalTransferPopup.defaultProps = {
        confirmText: 'Create',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(internalTransferPopup);

    return internalTransferPopup;
});
