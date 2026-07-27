import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { test, waitFor } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { unpatchSelf } from "@pos_self_order/app/plugins/pos_data_plugin";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("PosResGetQRtest", async () => {
    unpatchSelf();
    await setupAndMountPosApp({ set_tip_after_payment: false });
    if (PosUiUtils.isMobile()) {
        await contains(".pos-rightheader button:has([data-icon='menu'])").click();
        await contains(".o_pos_burger_menu_buttons button:has([data-icon='qr_code'])").click();
    } else {
        await contains(".floor-screen .qr-order-button").click();
    }
    await waitFor(
        ".modal-body p:contains(Enable QR menu in the Restaurant settings to get QR codes for free on tables.)"
    );
});
