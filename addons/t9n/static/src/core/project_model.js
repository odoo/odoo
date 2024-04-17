import { formatList } from "@web/core/l10n/utils";

export class Project {
    constructor(id, name, srcLang, targetLangs, resourceCount) {
        this.id = id;
        this.name = name;
        this.srcLang = srcLang;
        this.targetLangs = targetLangs;
        this.resourceCount = resourceCount;
    }

    get formattedTargetLanguages() {
        return formatList(this.targetLangs.map(({ name }) => name));
    }
}
