import { FormRenderer } from "@web/views/form/form_renderer";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            const context = this.props.record.context || {};
            const focusFieldName = context.default_focus;

            if (focusFieldName) {
                const input = document.querySelector(`[name=${focusFieldName}] input`);
                if (input) {
                    input.focus();
                }
            }
        });
    },
});
