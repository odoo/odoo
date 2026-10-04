import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { hasTouch } from "@web/core/browser/feature_detection";
import { utils } from "@web/core/ui/ui_utils";

export async function expandToolbar() {
    if (utils.isSmall() && hasTouch()) {
        // Nothing to do, the toolbar is always expanded in mobile.
    } else {
        await contains(".o-we-toolbar .btn[name='expand_toolbar']").click();
    }
    await waitFor(".o-we-toolbar[data-namespace='expanded']");
}
