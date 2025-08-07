import { BuilderAction } from "@html_builder/core/builder_action";
import { normalizeColor } from "@html_builder/utils/utils_css";
import { defaultImageFilterOptions } from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { getHtmlStyle } from "@html_editor/utils/formatting";
import { registry } from "@web/core/registry";

class ImageFilterOptionPlugin extends Plugin {
    static id = "ImageFilterOption";
    resources = {
        builder_actions: {
            GlFilterAction,
            SetCustomFilterAction,
        },
    };
}

export class GlFilterAction extends BuilderAction {
    static id = "glFilter";
    static dependencies = ["imagePostProcess"];
    isApplied({ editingElement, params: { mainParam: glFilterName } }) {
        if (glFilterName) {
            return editingElement.dataset.glFilter === glFilterName;
        } else {
            return !editingElement.dataset.glFilter;
        }
    }
    async load({ editingElement: img, params: { mainParam: glFilterName } }) {
        return await this.dependencies.imagePostProcess.processImage({
            img,
            newDataset: {
                glFilter: glFilterName,
            },
        });
    }
    apply({ loadResult: updateImageAttributes }) {
        updateImageAttributes();
    }
}
export class SetCustomFilterAction extends BuilderAction {
    static id = "setCustomFilter";
    static dependencies = ["imagePostProcess"];
    getValue({ editingElement, params: { mainParam: filterProperty } }) {
        const filterOptions = JSON.parse(editingElement.dataset.filterOptions || "{}");
        return filterOptions[filterProperty] || defaultImageFilterOptions[filterProperty];
    }
    isApplied({ editingElement, params: { mainParam: filterProperty }, value: filterValue }) {
        const filterOptions = JSON.parse(editingElement.dataset.filterOptions || "{}");
        return (
            filterValue ===
            (filterOptions[filterProperty] || defaultImageFilterOptions[filterProperty])
        );
    }
    async load({ editingElement: img, params: { mainParam: filterProperty }, value }) {
        const filterOptions = JSON.parse(img.dataset.filterOptions || "{}");
        filterOptions[filterProperty] =
            filterProperty === "filterColor"
                ? normalizeColor(value, getHtmlStyle(this.document))
                : value;
        return this.dependencies.imagePostProcess.processImage({
            img,
            newDataset: {
                filterOptions: JSON.stringify(filterOptions),
            },
        });
    }
    apply({ loadResult: updateImageAttributes }) {
        updateImageAttributes();
    }
}

registry.category("builder-plugins").add(ImageFilterOptionPlugin.id, ImageFilterOptionPlugin);
