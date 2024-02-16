import { Component } from "@odoo/owl";

export class ModuleToInstallIcon extends Component {
    static template = "website_slides.ModuleToInstallIcon";
    static props = {
        title: String,
        moduleId: Number,
        motivational: String,
        onClickInstallModuleIcon: Function,
    };
}

export class SlideCategoryIcon extends Component {
    static template = "website_slides.SlideCategoryIcon";
    static props = {
        slideCategory: String,
        categoryData: {
            type: Object,
            shape: {
                icon: String,
                label: String,
            },
        },
        onClickSlideCategoryIcon: Function,
    };
}
