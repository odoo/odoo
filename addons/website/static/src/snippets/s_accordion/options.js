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
     *
     * @see this.selectClass for parameters
     */
    customIcon: async function (previewMode, widgetValue, params) {
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
                this.faClassActiveCustomIcons = customClass;
                this.faClassInactiveCustomIcons = customClass;
                this.$target[0].dataset.activeCustomIcon = this.faClassActiveCustomIcons;
                this.$target[0].dataset.inactiveCustomIcon = this.faClassInactiveCustomIcons;
            }
        });
    },
});
