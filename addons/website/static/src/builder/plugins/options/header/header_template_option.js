import { BaseOptionComponent } from "@html_builder/core/utils";

export class HeaderTemplateOption extends BaseOptionComponent {
    static template = "website.HeaderTemplateOption";
<<<<<<< 189f0506f09249c5a7c2f7b7a5b02d9bd996014d
    static props = {};
||||||| 4a1299e5439fa44eb73d613fec843f06dabaf895
    static editableOnly = basicHeaderOptionSettings.editableOnly;
    static selector = basicHeaderOptionSettings.selector;
    static groups = basicHeaderOptionSettings.groups;
=======
>>>>>>> 2bf23d432e9f7e85c8be1c9b1630f6a133c956c8

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

Object.assign(HeaderTemplateOption, basicHeaderOptionSettings);
