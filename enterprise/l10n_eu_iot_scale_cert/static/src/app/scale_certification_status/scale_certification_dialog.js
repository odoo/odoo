import { Component } from "@odoo/owl";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ScaleCertificationDialog extends Component {
    static components = { Dialog };
    static props = {
        errors: {
            type: Array,
            element: String,
        },
        details: Object,
        checksum: String,
        autoFix: { type: Function, optional: true },
        close: Function,
    };
    static template = "pos_iot.ScaleCertificationDialog";

    setup() {
        this.notification = useService("notification");
        this.onClickTracked = useTrackedAsync(() => this.onClickFix());
    }

    onClickFix() {
        return this.props
            .autoFix()
            .then(() => {
                this.props.close();
            })
            .catch((error) => {
                this.notification.add(
                    _t(
                        "An error occurred while attempting to fix certification issues - %s",
                        error.message
                    ),
                    {
                        type: "danger",
                    }
                );
            });
    }
}
