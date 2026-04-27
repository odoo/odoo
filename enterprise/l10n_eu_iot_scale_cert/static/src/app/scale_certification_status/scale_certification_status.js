import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ScaleCertificationDialog } from "@l10n_eu_iot_scale_cert/app/scale_certification_status/scale_certification_dialog";

export class ScaleCertificationStatus extends Component {
    static props = {};
    static template = "pos_iot.ScaleCertificationStatus";

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.canAutoFix =
            this.pos.config._scale_checksum === this.pos.config._scale_checksum_expected;
    }

    openDialog() {
        this.dialog.add(ScaleCertificationDialog, {
            errors: this.pos.certificationErrors,
            checksum: this.pos.config._scale_checksum,
            details: this.pos.config._lne_certification_details,
            autoFix: this.canAutoFix ? this.fixCertificationErrors.bind(this) : undefined,
        });
    }

    async fixCertificationErrors() {
        await this.orm.call("pos.config", "fix_rounding_for_scale_certification");

        window.location.reload();
    }
}
