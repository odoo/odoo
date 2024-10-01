/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ViewButton } from "@web/views/view_button/view_button";
import { useSubEnv, onMounted, useEnv } from "@odoo/owl";

/*
* Common code for theme installation/update handler.
* It overrides the onClickViewButton function that's present in the env.
* That way, we display our own Loader and make a silent call to the ORM.
*/
export function useLoaderOnClick() {
    const website = useService('website');
    const orm = useService('orm');
    const action = useService('action');
    const env = useEnv();
    const previousOnClickViewButton = env.onClickViewButton;
    useSubEnv({
        async onClickViewButton(params) {
            const name = params.clickParams.name;
            if (['button_refresh_theme', 'button_choose_theme'].includes(name)) {
                website.invalidateSnippetCache = true;
                website.showLoader({ showTips: name !== 'button_refresh_theme' });
                try {
                    const resParams = params.getResParams();
                    const callback = await orm.silent.call(resParams.resModel, name, [[resParams.resId]]);
                    let keepLoader = false;
                    if (callback) {
                        callback.target = 'main';
                        await action.doAction(callback);
                        if (callback.tag === 'website_preview' && callback.context.params.with_loader) {
                            keepLoader = true;
                        }
                    }
                    if (!keepLoader) {
                        website.hideLoader();
                    }
                } catch (error) {
                    website.hideLoader();
                    throw error;
                }
            } else {
                return previousOnClickViewButton(...arguments);
            }
        }
    });
}

class ThemePreviewFormController extends FormController {
    static components = { ...FormController.components, ViewButton };
    static template = "website.ThemePreviewFormController";
    /**
     * @override
     */
    setup() {
        super.setup();
        useLoaderOnClick();

        // TODO adapt theme previews then remove this
        onMounted(() => {
            setTimeout(() => {
                document.querySelector('button[name="button_choose_theme"]')?.click();
            }, 0);
        });
    }
    /**
     * @override
     */
    get className() {
        return {...super.className, 'o_view_form_theme_preview_controller': true};
    }
    /**
     * Handler called when user click on 'Choose another theme' button.
     */
    back() {
        this.env.config.historyBack();
    }
}

class ThemePreviewFormControlPanel extends ControlPanel {
    static template = "website.ThemePreviewForm.ControlPanel";
    /**
     * Triggers an event on the main bus.
     * @see {FieldIframePreview} for the event handler.
     */
    onMobileClick() {
        this.env.bus.trigger('THEME_PREVIEW:SWITCH_MODE', {mode: 'mobile'});
    }
    /**
     * @see {onMobileClick}
     */
    onDesktopClick() {
        this.env.bus.trigger('THEME_PREVIEW:SWITCH_MODE', {mode: 'desktop'});
    }
    /**
     * Handler called when user click on Go Back button.
     */
    back() {
        this.env.config.historyBack();
    }
}

const ThemePreviewFormView = {
    ...formView,
    Controller: ThemePreviewFormController,
    ControlPanel: ThemePreviewFormControlPanel,
};

registry.category('views').add('theme_preview_form', ThemePreviewFormView);
