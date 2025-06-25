import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Typing } from "@mail/discuss/typing/common/typing";

import { patch } from "@web/core/utils/patch";

patch(ThreadIcon, {
    components: { ...ThreadIcon.components, Typing },
});
