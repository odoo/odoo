import { CopyButton, copyButtonProps } from "@web/core/copy_button/copy_button";
import { useService } from "@web/core/utils/hooks";
import { t, useProps } from "@odoo/owl";

export class GenerateContentAndCopyButton extends CopyButton {
    props = useProps({
        ...copyButtonProps,
        contentGenerationFunction: t.function().optional(),
    });

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onClick() {
        if(this.props.contentGenerationFunction){
            this.props.content = await this.props.contentGenerationFunction();
        }
        await super.onClick();
    }
}
