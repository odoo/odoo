<<<<<<< HEAD
||||||| MERGE BASE
=======
import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GloryErrorDialog extends Component {
    static template = "pos_glory_cash.GloryErrorDialog";
    static components = { Dialog };
    props = useProps({
        errorCode: t.string(),
        errorGif: t.string(),
        reset: t.function([]),
        close: t.function([]),
    });
}

>>>>>>> FORWARD PORTED
