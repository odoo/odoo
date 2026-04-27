import MainComponent from "@stock_barcode/components/main";
import { patch } from "@web/core/utils/patch";

patch(MainComponent.prototype, {
    setup() {
        super.setup();
    },

    async onOpenProductForm() {
        await this.env.model.save();
        this.env.model.openProductForm();
    }
});
