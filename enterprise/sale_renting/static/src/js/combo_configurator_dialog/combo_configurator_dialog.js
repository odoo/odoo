import { patch } from '@web/core/utils/patch';
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';

patch(ComboConfiguratorDialog, {
    props: {
        ...ComboConfiguratorDialog.props,
        rentalStartDate: { type: String, optional: true },
        rentalEndDate: { type: String, optional: true },
    },
});

patch(ComboConfiguratorDialog.prototype, {
    _getAdditionalRpcParams() {
        const params = super._getAdditionalRpcParams();
        if (this.props.rentalStartDate && this.props.rentalEndDate) {
            params.start_date = this.props.rentalStartDate;
            params.end_date = this.props.rentalEndDate;
        }
        return params;
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        if (this.props.rentalStartDate && this.props.rentalEndDate) {
            props.rentalStartDate = this.props.rentalStartDate;
            props.rentalEndDate = this.props.rentalEndDate;
        }
        return props;
    },
});
