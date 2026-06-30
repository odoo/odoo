import { useChildSubEnv } from "@web/owl2/utils";
import { Component, props, t } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class ScaleScreen extends Component {
    static template = "point_of_sale.ScaleScreen";
    static components = { Dialog };
    props = props({
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.dialog = useService("dialog");
        this.pos = usePos();
        this.scale = this.pos.scale;
        this.scale.setErrorCallback(this.onError.bind(this));
        useChildSubEnv({ dialogData: { ...this.env.dialogData, close: this.close.bind(this) } });
    }

    confirm() {
        this.props.getPayload(this.scale.confirmWeight());
        this.close();
    }

    close() {
        this.props.close();
        this.scale.setErrorCallback(null);
        this.scale.product = null;
    }

    onError(message, isFatalError) {
        if (isFatalError) {
            this.props.getPayload(null);
        }
        this.dialog.add(
            AlertDialog,
            {
                title: _t("Scale error"),
                body: message,
            },
            { onClose: isFatalError ? this.close.bind(this) : undefined }
        );
    }
}
