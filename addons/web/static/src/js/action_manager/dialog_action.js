odoo.define('web.DialogAction', function (require) {
    "use strict";

    const OwlDialog = require('web.OwlDialog');

    class DialogAction extends owl.Component {
        constructor() {
            super(...arguments);
            this.dialog = owl.hooks.useRef('dialog');
            this.legacyActionWigdet = null;
            this.env.bus.on('legacy-action', this, (legacyWidget) => {
                this.legacyActionWigdet = legacyWidget;
            });
        }
        __patch() {
            const patched = super.__patch(...arguments);
            if (this.legacyActionWigdet) {
                const footer = this.dialog.comp.footerRef.el;
                footer.innerHTML = "";
                this.legacyActionWigdet.renderButtons($(footer));
            }
            return patched;
        }
    }
    DialogAction.template = owl.tags.xml`
        <OwlDialog t-props="props" t-ref="dialog">
            <t t-slot="default"/>
        </OwlDialog>`;
    DialogAction.components = { OwlDialog };

    return DialogAction;
});