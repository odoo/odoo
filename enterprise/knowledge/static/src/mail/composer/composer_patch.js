import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

// TODO ABD: could be replaced by a KnowledgeComposer ?
/** @type {Composer} */
const composerPatch = {
    get hasGifPicker() {
        // Done to remove the gif picker when in Knowledge as per the specs
        return super.hasGifPicker && !this.env.inKnowledge;
    },
};
patch(Composer.prototype, composerPatch);
