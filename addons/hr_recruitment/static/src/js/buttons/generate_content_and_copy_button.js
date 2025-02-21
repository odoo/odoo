import { CopyButton } from "@web/core/copy_button/copy_button";
import { useService } from "@web/core/utils/hooks";

export class GenerateContentAndCopyButton extends CopyButton {
    static props = {
        ...CopyButton.props,
        contentGenerationFunction: { type: Function, optional: true },
    };

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
