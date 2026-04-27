import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ScaleCertificationStatus } from "@l10n_eu_iot_scale_cert/app/scale_certification_status/scale_certification_status";

patch(Navbar, {
    components: { ...Navbar.components, ScaleCertificationStatus },
});
