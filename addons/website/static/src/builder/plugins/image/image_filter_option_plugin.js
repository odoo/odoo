import { normalizeColor } from "@html_builder/utils/utils_css";
import { defaultImageFilterOptions } from "@html_editor/main/media/image_post_process_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ImageFilterOptionPlugin extends Plugin {
    static id = "ImageFilterOption";
    static dependencies = ["imagePostProcess"];
    resources = {
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            glFilter: {
                isApplied: ({ editingElement, params: { mainParam: glFilterName } }) => {
                    if (glFilterName) {
                        return editingElement.dataset.glFilter === glFilterName;
                    } else {
                        return !editingElement.dataset.glFilter;
                    }
                },
                load: async ({ editingElement: img, params: { mainParam: glFilterName } }) =>
                    await this.dependencies.imagePostProcess.processImage(img, {
                        glFilter: glFilterName,
                    }),
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            setCustomFilter: {
                getValue: ({ editingElement, params: { mainParam: filterProperty } }) => {
                    const filterOptions = JSON.parse(editingElement.dataset.filterOptions || "{}");
                    return (
                        filterOptions[filterProperty] || defaultImageFilterOptions[filterProperty]
                    );
                },
                isApplied: ({
                    editingElement,
                    params: { mainParam: filterProperty },
                    value: filterValue,
                }) => {
                    const filterOptions = JSON.parse(editingElement.dataset.filterOptions || "{}");
                    return (
                        filterValue ===
                        (filterOptions[filterProperty] || defaultImageFilterOptions[filterProperty])
                    );
                },
                load: async ({
                    editingElement: img,
                    params: { mainParam: filterProperty },
                    value,
                }) => {
                    const filterOptions = JSON.parse(img.dataset.filterOptions || "{}");
                    filterOptions[filterProperty] =
                        filterProperty === "filterColor" ? normalizeColor(value) : value;
                    return this.dependencies.imagePostProcess.processImage(img, {
                        filterOptions: JSON.stringify(filterOptions),
                    });
                },
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
        };
    }
}
registry.category("website-plugins").add(ImageFilterOptionPlugin.id, ImageFilterOptionPlugin);
