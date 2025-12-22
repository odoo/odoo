import { models } from "@web/../tests/web_test_helpers";

export class SlideChannel extends models.ServerModel {
    _name = "slide.channel";
    _views = {
        form: /* xml */ `
            <form>
                <chatter/>
            </form>
        `,
    };
}
