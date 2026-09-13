import { Component, t, useProps } from "@odoo/owl";

export class ModuleToInstallIcon extends Component {
    static template = "website_slides.ModuleToInstallIcon";

    props = useProps({
        title: t.string(),
        moduleId: t.number(),
        motivational: t.string(),
        onClickInstallModuleIcon: t.function(),
    });
}

export class SlideCategoryIcon extends Component {
    static template = "website_slides.SlideCategoryIcon";

    props = useProps({
        slideCategory: t.string(),
        categoryData: t.object({
            icon: t.string(),
            iconClass: t.string().optional(),
            label: t.string(),
        }),
        onClickSlideCategoryIcon: t.function(),
    });
}
