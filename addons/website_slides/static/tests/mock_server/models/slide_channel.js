import { models } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_VIEW_ID } from "@mail/../tests/mock_server/mock_models/constants";

export class SlideChannel extends models.ServerModel {
    _name = "slide.channel";
    _views = {
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: `
            <form>
                <chatter/>
            </form>
        `,
    };
}
