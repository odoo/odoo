import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import options from "@web_editor/js/editor/snippets.options";

options.registry.Accordion = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this.faClassActiveCustomIcons = this.$target[0].dataset.activeCustomIcon || '';
        this.faClassInactiveCustomIcons = this.$target[0].dataset.inactiveCustomIcon || '';
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to select a font awesome icon with media dialog.
     */
    async defineCustomIcon(previewMode, widgetValue, params) {
        const media = document.createElement('i');
        media.className = params.customActiveIcon === 'true' ? this.faClassActiveCustomIcons : this.faClassInactiveCustomIcons;
        this.call("dialog", "add", MediaDialog, {
            noImages: true,
            noDocuments: true,
            noVideos: true,
            media,
            save: icon => {
                const customClass = icon.className;
                const activeIcons = this.$target[0].querySelectorAll('.o_custom_icon_active i');
                const inactiveIcons = this.$target[0].querySelectorAll('.o_custom_icon_inactive i');
                const icons = params.customActiveIcon === 'true' ? activeIcons : inactiveIcons;
                icons.forEach(icon => {
                    icon.removeAttribute('class');
                    icon.classList.add(...customClass.split(" "));
                });
                if (icons === activeIcons) {
                    this.faClassActiveCustomIcons = customClass;
                } else {
                    this.faClassInactiveCustomIcons = customClass;
                }
                this.$target[0].dataset.activeCustomIcon = this.faClassActiveCustomIcons;
                this.$target[0].dataset.inactiveCustomIcon = this.faClassInactiveCustomIcons;
            }
        });
    },
    /**
     * Allows to add the necessary HTML structure for custom icons
     */
    customIcon(previewMode, widgetValue, params) {
        const accordionButtonEls = this.$target[0].querySelectorAll('.accordion-button');
        const activeCustomIcon = this.$target[0].dataset.activeCustomIcon;
        const inactiveCustomIcon = this.$target[0].dataset.inactiveCustomIcon;
        const customIcons = params.selectIcons ?
            `<span class="o_custom_icon_active position-absolute top-0 end-0 bottom-0 start-0 d-flex align-items-center justify-content-center">
                <i class="${activeCustomIcon}"></i>
            </span>
            <span class="o_custom_icon_inactive position-absolute top-0 end-0 bottom-0 start-0 d-flex align-items-center justify-content-center">
                <i class="${inactiveCustomIcon}"></i>
            </span>` : '';
        if (widgetValue) {
            accordionButtonEls.forEach(item => {
                const customIconWrapEl = item.querySelector('.o_custom_icons_wrap');
                if (customIconWrapEl) {
                    customIconWrapEl.innerHTML = customIcons;
                } else {
                    const newCustomIconWrapEl = document.createElement("span");
                    newCustomIconWrapEl.className = "o_custom_icons_wrap position-relative d-block flex-shrink-0 overflow-hidden";
                    item.appendChild(newCustomIconWrapEl);
                    newCustomIconWrapEl.innerHTML = customIcons;
                }
            });
        } else {
            accordionButtonEls.forEach(item => {
                const customIconWrapEl = item.querySelector('.o_custom_icons_wrap');
                if (customIconWrapEl) {
                    customIconWrapEl.remove();
                }
            });
        }
    },
});
