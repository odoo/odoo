import { initializeDesignTabCss } from "@mass_mailing/js/mass_mailing_design_constants";
import { Component, onWillStart, useEffect, useState } from "@odoo/owl";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} TemplateInfos
 * @property {string} name
 * @property {string} template
 * @property {[boolean]} nowrap
 * @property {[string]} className
 * @property {[string]} layoutStyles
 * @property {[function]} get_image_info
 */

/**
 * Swap the previous theme's default images with the new ones.
 * (Redefine the `src` attribute of all images in a $container, depending on the theme parameters.)
 *
 * @private
 * @param {Object} themeParams
 * @param {JQuery} $container
 */
export function switchImages(themeParams, $container) {
    if (!themeParams) {
        return;
    }
    for (const img of $container.find("img")) {
        const $img = $(img);
        const src = $img.attr("src");
        $img.removeAttr("loading");

        let m = src.match(/^\/web\/image\/\w+\.s_default_image_(?:theme_[a-z]+_)?(.+)$/);
        if (!m) {
            m = src.match(
                /^\/\w+\/static\/src\/img\/(?:theme_[a-z]+\/)?s_default_image_(.+)\.[a-z]+$/
            );
        }
        if (!m) {
            return;
        }

        if (themeParams.get_image_info) {
            const file = m[1];
            const imgInfo = themeParams.get_image_info(file);

            const src = imgInfo.format
                ? `/${imgInfo.module}/static/src/img/theme_${themeParams.name}/s_default_image_${file}.${imgInfo.format}`
                : `/web/image/${imgInfo.module}.s_default_image_theme_${themeParams.name}_${file}`;

            $img.attr("src", src);
        }
    }
}

export class MassMailingTemplateSelector extends Component {
    static template = "mass_mailing.MassMailingTemplateSelector";
    static props = {
        mailingModelId: Number,
        mailingModelName: String,
        filterTemplates: Boolean,
        onSelectMassMailingTemplate: Function,
    };
    setup() {
        this.state = useState({
            allTemplates: [],
            templates: [],
            themes: [],
        });
        this.orm = useService("orm");
        this.action = useService("action");
        onWillStart(async () => {
            [this.state.allTemplates, this.state.themes] = await Promise.all([
                this.loadTemplates(),
                this.loadTheme(),
            ]);
        });

        useEffect(
            (allTemplates, mailingModelId) => {
                this.state.templates = allTemplates.filter(
                    (template) => template.modelId === mailingModelId
                );
            },
            () => [this.state.allTemplates, this.props.mailingModelId]
        );
    }

    async loadTemplates() {
        // Filter the fetched templates based on the current model
        const args = this.props.filterTemplates
            ? [[["mailing_model_id", "=", this.props.mailingModelId]]]
            : [];

        // Templates taken from old mailings
        const favoritesTemplates = await this.orm.call(
            "mailing.mailing",
            "action_fetch_favorites",
            args
        );
        return favoritesTemplates.map((template) => {
            return {
                id: template.id,
                modelId: template.mailing_model_id[0],
                modelName: template.mailing_model_id[1],
                name: `template_${template.id}`,
                nowrap: true,
                subject: template.subject,
                template: template.body_arch,
                userId: template.user_id[0],
                userName: template.user_id[1],
            };
        });
    }
    async loadTheme() {
        const themesHTML = await this.orm.call("ir.ui.view", "render_public_asset", [
            "mass_mailing.email_designer_themes",
        ]);
        const themesEls = new DOMParser().parseFromString(themesHTML, "text/html").body.children;

        // Initialize theme parameters.
        const displayableThemes = uiUtils.isSmall()
            ? Array.from(themesEls).filter((theme) => !theme.dataset.hideFromMobile)
            : themesEls;
        return Array.from(displayableThemes).map((theme) => {
            const $theme = $(theme);
            const name = $theme.data("name");
            const classname = "o_" + name + "_theme";
            const imagesInfo = Object.assign(
                {
                    all: {},
                },
                $theme.data("imagesInfo") || {}
            );
            for (const [key, info] of Object.entries(imagesInfo)) {
                imagesInfo[key] = Object.assign(
                    {
                        module: "mass_mailing",
                        format: "jpg",
                    },
                    imagesInfo.all,
                    info
                );
            }
            return {
                name: name,
                title: $theme.attr("title") || "",
                className: classname || "",
                img: $theme.data("img") || "",
                template: $theme.html().trim(),
                nowrap: !!$theme.data("nowrap"),
                get_image_info: function (filename) {
                    if (imagesInfo[filename]) {
                        return imagesInfo[filename];
                    }
                    return imagesInfo.all;
                },
                layoutStyles: $theme.data("layout-styles"),
            };
        });
    }
    /**
     * @param {TemplateInfos} templateInfos
     */
    async selectTemplate(templateInfos) {
        this.props.onSelectMassMailingTemplate(
            templateInfos,
            await this.getTemplateHTML(templateInfos)
        );
    }
    /**
     * @param {TemplateInfos} templateInfos
     */
    async getTemplateHTML(templateInfos) {
        let $newWrapper;
        let $newWrapperContent;
        if (templateInfos.nowrap) {
            $newWrapper = $("<div/>", {
                class: "oe_structure",
            });
            $newWrapperContent = $newWrapper;
        } else {
            // This wrapper structure is the only way to have a responsive
            // and centered fixed-width content column on all mail clients
            $newWrapper = $("<div/>", {
                class: "container o_mail_wrapper o_mail_regular oe_unremovable",
            });
            $newWrapperContent = $("<div/>", {
                class: "col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable",
            });
            $newWrapper.append($('<div class="row"/>').append($newWrapperContent));
        }
        const $newLayout = $("<div/>", {
            class: "o_layout oe_unremovable oe_unmovable bg-200 " + templateInfos.className,
            style: templateInfos.layoutStyles,
            "data-name": "Mailing",
        }).append($newWrapper);

        const $contents = templateInfos.template;
        $newWrapperContent.append($contents);
        switchImages(templateInfos, $newWrapperContent);
        initializeDesignTabCss($newLayout);

        return $newLayout[0].outerHTML;
    }

    async deleteTemplate(templateId) {
        const action = await this.orm.call("mailing.mailing", "action_remove_favorite", [
            templateId,
        ]);
        this.action.doAction(action);
        this.state.allTemplates = this.state.allTemplates.filter(
            (template) => template.id !== templateId
        );
    }
}
