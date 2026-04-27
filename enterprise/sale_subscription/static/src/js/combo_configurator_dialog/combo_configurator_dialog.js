import { patch } from '@web/core/utils/patch';
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';

patch(ComboConfiguratorDialog, {
    props: {
        ...ComboConfiguratorDialog.props,
        subscriptionPlanId: { type: Number, optional: true },
    },
});

patch(ComboConfiguratorDialog.prototype, {
    _getAdditionalRpcParams() {
        const params = super._getAdditionalRpcParams();
        if (this.props.subscriptionPlanId) {
            params.plan_id = this.props.subscriptionPlanId;
        }
        return params;
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        if (this.props.subscriptionPlanId) {
            props.subscriptionPlanId = this.props.subscriptionPlanId;
        }
        return props;
    },
});
