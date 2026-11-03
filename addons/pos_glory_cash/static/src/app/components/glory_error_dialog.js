import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GloryErrorDialog extends Component {
    static template = "pos_glory_cash.GloryErrorDialog";
    static components = { Dialog };
    props = useProps({
        errorCode: t.string().optional(),
        errorGif: t.string().optional(),
        message: t.string().optional(),
        reset: t.function([]).optional(),
        close: t.function([]),
    });
}
