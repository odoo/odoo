import { registry } from "@web/core/registry";
import {
    AnimateOverflow,
    blockHoverTransformSelector,
} from "@website/interactions/animate_overflow";

const AnimateOverflowEdit = (I) =>
    class extends I {
        // The public interaction listens directly on hover blocks found when it
        // starts. In edit mode, hover effects can be added later, so listen on
        // the stable root and let the transition events bubble up from newly
        // animated blocks.
        dynamicContent = {
            ...this.dynamicContent,
            [blockHoverTransformSelector]: {},
            _root: {
                ...this.dynamicContent._root,
                "t-on-transitionstart.noUpdate": this.onBlockHoverTransitionStart,
                "t-on-transitionend.noUpdate": this.onBlockHoverTransitionEnd,
            },
        };
    };

registry.category("public.interactions.edit").add("website.animate_overflow", {
    Interaction: AnimateOverflow,
    mixin: AnimateOverflowEdit,
});
