import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function expandToolbar() {
    await contains(".o-we-toolbar .btn[name='expand_toolbar'").click();
    await waitFor(".o-we-toolbar[data-namespace='expanded']");
}
