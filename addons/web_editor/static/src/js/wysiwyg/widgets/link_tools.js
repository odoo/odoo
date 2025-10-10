/** @odoo-module **/

import { Link } from "./link";
import { ColorPalette } from '@web_editor/js/wysiwyg/widgets/color_palette';
import weUtils from "@web_editor/js/common/utils";
import {
    onMounted,
    onWillUnmount,
    onWillDestroy,
    useState,
} from "@odoo/owl";
import { normalizeCSSColor } from '@web/core/utils/colors';
import { useService } from "@web/core/utils/hooks";
import { isButton } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";

/**
 * Allows to customize link content and style.
 */
export class LinkTools extends Link {
    static template = 'web_editor.LinkTools';
    static props = {
        ...Link.props,
        wysiwyg: { type: Object },
        $button: { type: Object },
        onColorCombinationClassChange: { type: Function, optional: true },
        onPreApplyLink: { type: Function, optional: true },
        onPostApplyLink: { type: Function, optional: true },
        onDestroy: { type: Function, optional: true },
        getColorpickerTemplate: { type: Function, optional: true },
    };
    static defaultProps = {
        ...Link.defaultProps,
        onColorCombinationClassChange: () => {},
        onPreApplyLink: () => {},
        onPostApplyLink: () => {},
        onDestroy: () => {},
    };
    static components = { ColorPalette };
    colorpickerProps = useState({
        'color': { selectedColor: undefined },
        'background-color': { selectedColor: undefined },
        'border-color': { selectedColor: undefined },
    });
    colorpickers = {
        'color': { colorNames: null },
        'background-color': { colorNames: null },
        'border-color': { colorNames: null },
    };
    state = useState({
        showLinkSizeRow: true,
        showLinkCustomColor: true,
        showLinkShapeRow: true,
        isDocument: false,
        directDownload: true,
    });

    setup() {
        super.setup(...arguments);
        onMounted(() => {
            this._observer = new MutationObserver(records => {
                if (records.some(record => record.type === 'attributes')) {
                    this.state.url = this.props.link.getAttribute('href') || '';
                    this._setUrl();
                }
                this._updateLabelInput();
            });
            this._observerOptions = {
                subtree: true,
                childList: true,
                characterData: true,
                attributes: true,
                attributeFilter: ['href'],
            };
            this._observer.observe(this.props.link, this._observerOptions);
        });
        onWillUnmount(() => {
            this._observer.disconnect();
        });
        onWillDestroy(() => {
            const $contents = this.$link.contents();
            if (shouldUnlink(this.$link[0], this.colorCombinationClass)) {
                $contents.unwrap();
            }
            this.props.onDestroy();
        });
        this.uploadService = useService('uploadLocalFiles');
    }
    /**
     * @override
     */
    async willUpdateProps(newProps) {
        await super.willUpdateProps(newProps);
        this.$link = newProps.link ? $(newProps.link) : this.link;
        this._setSelectOptionFromLink();
        this._updateOptionsUI();
        this._updateLabelInput();
        this._checkDocumentState();
    }

    /**
     * @override
     */
    async _updateState() {
        await super._updateState(...arguments);
        // Keep track of each selected custom color and colorpicker.
        this.customColors = {};
        this.PREFIXES = {
            'color': 'text-',
            'background-color': 'bg-',
        };
        this._updateInitialNewWindowUI();
    }
    _updateInitialNewWindowUI() {
        // TODO In master, put initialNewWindow in state.
        // Adjust rendered initialNewWindow because changes are ignored by Owl.
        if (this.$el && this.$el[0]) {
            const checkboxEl = this.$el[0].querySelector("we-checkbox[name='is_new_window'");
            if (checkboxEl) {
                checkboxEl.checked = this.initialNewWindow ? "checked" : "";
                const buttonEl = checkboxEl.closest("we-button");
                if (buttonEl) {
                    buttonEl.classList[this.initialNewWindow ? "add" : "remove"]("active");
                }
            }
        }
    }
    /**
     * @override
     */
    async start() {
        const ret = await super.start(...arguments);
        this.$el.on('click', 'we-select we-button', this._onPickSelectOption.bind(this));
        this.$el.on('click', 'we-checkbox', this._onClickCheckbox.bind(this));
        this.$el.on('change', '.link-custom-color-border input', this._onChangeCustomBorderWidth.bind(this));
        this.$el.on('keypress', '.link-custom-color-border input', this._onKeyPressCustomBorderWidth.bind(this));
        this.$el.on('click', 'we-select [name="link_border_style"] we-button', this._onBorderStyleSelectOption.bind(this));
        this.$el.on('input', 'input[name="label"]', this._onLabelInput.bind(this));

        this._setSelectOptionFromLink();
        this._updateOptionsUI();

        if (!this.linkEl.href && this.state.url) {
            // Link URL was deduced from label. Apply changes to DOM.
            this.__onURLInput();
        }
        this._checkDocumentState();

        return ret;
    }
    applyLinkToDom() {
        this._observer.disconnect();
        this.props.onPreApplyLink();
        super.applyLinkToDom(...arguments);
        this.props.wysiwyg.odooEditor.historyStep();
        this.props.onPostApplyLink();
        this._observer.observe(this.props.link, this._observerOptions);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    focusUrl() {
        this.$el[0].scrollIntoView();
        super.focusUrl(...arguments);
    }

    /**
     * Method no longer used, kept for compatibility (stable policy).
     * To be removed in master.
     */
    openDocumentDialog() {
        this.props.wysiwyg.openMediaDialog({
            resModel: "ir.ui.view",
            useMediaLibrary: true,
            noImages: true,
            noIcons: true,
            noVideos: true,
            save: async (link) => {
                this.initialNewWindow = this.initialIsNewWindowFromProps;
                this._updateInitialNewWindowUI();
                let relativeUrl = link.href.substr(window.location.origin.length);
                await this._determineAttachmentType(relativeUrl.split("?")[0]);
                if (this.isLastAttachmentUrl) {
                    relativeUrl = relativeUrl.replace("&download=true", "");
                }
                this.$el[0].querySelector("#o_link_dialog_url_input").value = relativeUrl;
                this.__onURLInput();
            },
        });
    }

    async uploadFile() {
        const { upload, getURL } = this.uploadService;
        const [attachment] = await upload({ resModel: "ir.ui.view" });
        if (!attachment) {
            // No file selected or upload failed
            return;
        }
        let relativeUrl = getURL(attachment, { download: true, unique: true });
        this.initialNewWindow = this.initialIsNewWindowFromProps;
        this._updateInitialNewWindowUI();
        this.lastAttachmentId = attachment.id;
        this.isLastAttachmentUrl = false;
        this.$el[0].querySelector("#o_link_dialog_url_input").value = relativeUrl;
        this.__onURLInput();
    }
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _setSelectOptionFromLink() {
        super._setSelectOptionFromLink(...arguments);
        const link = this.$link[0];
        const customStyleProps = ['color', 'background-color', 'background-image', 'border-width', 'border-style', 'border-color'];
        const shapeClasses = ['btn-outline-primary', 'btn-outline-secondary', 'btn-fill-primary', 'btn-fill-secondary', 'rounded-circle', 'flat'];
        if (customStyleProps.some(s => link.style[s]) || shapeClasses.some(c => link.classList.contains(c))) {
            // Force custom style if style or shape exists on the link.
            const customOption = this.$el[0].querySelector('[name="link_style_color"] we-button[data-value="custom"]');
            this._setSelectOption($(customOption), true);
        }
    }
    /**
     * @override
     */
    _adaptPreview() {
        var data = this._getData();
        if (data === null) {
            return;
        }
        this.applyLinkToDom(data);
    }
    /**
     * @override
     */
    _doStripDomain() {
        return this.$el.find('we-checkbox[name="do_strip_domain"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
    }
    /**
     * @override
     */
    _getIsNewWindowFormRow() {
        return this.$el.find('we-checkbox[name="is_new_window"]').closest('we-row');
    }
    /**
     * @override
     */
    _getLinkOptions() {
        const options = [
            'we-selection-items[name="link_style_color"] > we-button',
            'we-selection-items[name="link_style_size"] > we-button',
            'we-selection-items[name="link_style_shape"] > we-button',
        ];
        return this.$el.find(options.join(','));
    }
    /**
     * @override
     */
    _getLinkShape() {
        return this.$el.find('we-selection-items[name="link_style_shape"] we-button.active').data('value') || '';
    }
    /**
     * @override
     */
    _getLinkSize() {
        return this.$el.find('we-selection-items[name="link_style_size"] we-button.active').data('value') || '';
    }
    /**
     * @override
     */
    _getLinkType() {
        return this.$el.find('we-selection-items[name="link_style_color"] we-button.active').data('value') || '';
    }
    /**
     * @override
     */
    _getLinkCustomTextColor() {
        return this.customColors['color'];
    }
    /**
     * @override
     */
    _getLinkCustomBorder() {
        return this.customColors['border-color'];
    }
    /**
     * @override
     */
    _getLinkCustomBorderWidth() {
        return this.$el.find('.link-custom-color-border input').val() || '';
    }
    /**
     * @override
     */
    _getLinkCustomBorderStyle() {
        return this.$el.find('.link-custom-color-border we-button.active').data('value') || '';
    }
    /**
     * @override
     */
    _getLinkCustomFill() {
        return this.customColors['background-color'];
    }
    /**
     * @override
     */
    _getLinkCustomClasses() {
        let textClass = this.customColors['color'];
        const colorPickerFg = this.colorpickers['color'].colorNames;
        if (
            !textClass ||
            !colorPickerFg ||
            !weUtils.computeColorClasses(colorPickerFg, 'text-').includes(textClass)
        ) {
            textClass = '';
        }
        let fillClass = this.customColors['background-color'];
        const colorPickerBg = this.colorpickers['background-color'].colorNames;
        if (
            !fillClass ||
            !colorPickerBg ||
            !weUtils.computeColorClasses(colorPickerBg, 'bg-').includes(fillClass)
        ) {
            fillClass = '';
        }
        return ` ${textClass} ${fillClass}`;
    }
    /**
     * @override
     */
    _isNewWindow(url) {
        if (this.props.forceNewWindow) {
            return this._isFromAnotherHostName(url);
        } else {
            return this.$el.find('we-checkbox[name="is_new_window"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
        }
    }
    /**
     * @override
     */
    _setSelectOption($option, active) {
        $option.toggleClass('active', active);
        if (active) {
            $option.closest('we-select').find('we-toggler').text($option.text());
            // ensure only one option is active in the dropdown
            $option.siblings('we-button').removeClass("active");
        }
    }
    /**
     * @override
     */
    _updateOptionsUI() {
        const el = this.$el[0].querySelector('[name="link_style_color"] we-button.active');
        if (el) {
            this.colorCombinationClass = el.dataset.value;
            // Hide the size option if the link is an unstyled anchor.
            this.state.showLinkSizeRow = Boolean(this.colorCombinationClass);

            // // Show custom colors and shape only for Custom style.
            this.state.showLinkCustomColor = el.dataset.value === 'custom';
            this.state.showLinkShapeRow = el.dataset.value === 'custom';

            this.props.onColorCombinationClassChange(this.colorCombinationClass);

            this._updateColorpicker('color');
            this._updateColorpicker('background-color');
            this._updateColorpicker('border-color');

            const borderWidth = this.linkEl.style['border-width'];
            const numberAndUnit = weUtils.getNumericAndUnit(borderWidth);
            this.$el.find('.link-custom-color-border input').val(numberAndUnit ? numberAndUnit[0] : "1");
            let borderStyle = this.linkEl.style['border-style'];
            if (!borderStyle || borderStyle === 'none') {
                borderStyle = 'solid';
            }
            const $activeBorderStyleButton = this.$el.find(`.link-custom-color-border [name="link_border_style"] we-button[data-value="${borderStyle}"]`);
            $activeBorderStyleButton.addClass('active');
            $activeBorderStyleButton.siblings('we-button').removeClass("active");
            const $activeBorderStyleToggler = $activeBorderStyleButton.closest('we-select').find('we-toggler');
            $activeBorderStyleToggler.empty();
            $activeBorderStyleButton.find('div').clone().appendTo($activeBorderStyleToggler);
        }
    }
    /**
     * Updates the colorpicker associated to a given property - updated with its selected color.
     *
     * @private
     * @param {string} cssProperty
     */
    _updateColorpicker(cssProperty) {
        const prefix = this.PREFIXES[cssProperty];

        // Update selected color.
        const colorNames = this.colorpickers[cssProperty].colorNames;
        let color = this.linkEl.style[cssProperty];
        const colorClasses = prefix ? weUtils.computeColorClasses(colorNames, prefix) : [];
        const colorClass = prefix && weUtils.getColorClass(this.linkEl, colorNames, prefix);
        const isColorClass = colorClasses.includes(colorClass);
        if (isColorClass) {
            color = colorClass;
        } else if (cssProperty === 'background-color') {
            const gradientColor = this.linkEl.style['background-image'];
            if (weUtils.isColorGradient(gradientColor)) {
                color = gradientColor;
            }
        }
        this.customColors[cssProperty] = color;
        if (cssProperty === 'border-color') {
            // Highlight matching named color if any.
            const colorName = colorNames[normalizeCSSColor(color)];
            this.colorpickerProps[cssProperty].selectedColor = colorName || color;
        } else {
            this.colorpickerProps[cssProperty].selectedColor = isColorClass ? color.replace(prefix, '') : color;
        }

        // Update preview.
        const $colorPreview = this.$el.find('.link-custom-color-' + (cssProperty === 'border-color' ? 'border' : cssProperty === 'color' ? 'text' : 'fill') + ' .o_we_color_preview');
        const previewClasses = weUtils.computeColorClasses(colorNames, 'bg-');
        $colorPreview[0].classList.remove(...previewClasses);
        if (isColorClass) {
            $colorPreview.css('background-color', `var(--we-cp-${color.replace(prefix, '')}`);
            $colorPreview.css('background-image', '');
        } else {
            $colorPreview.css('background-color', weUtils.isColorGradient(color) ? 'rgba(0, 0, 0, 0)' : color);
            $colorPreview.css('background-image', weUtils.isColorGradient(color) ? color : '');
        }
    }

    /**
     * @private
     */
    _onColorpaletteSetColorNames(cssProperty, colorNames) {
        this.colorpickers[cssProperty].colorNames = colorNames;
    }
    /**
     * @private
     */
    _onColorpaletteColorPicked(cssProperty, params) {
        // Reset color styles in link content to make sure new color is not hidden.
        // Only done when applied to avoid losing state during preview.
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(this.linkEl);
        selection.removeAllRanges();
        selection.addRange(range);
        this.props.wysiwyg.odooEditor.execCommand('applyColor', '', 'color');
        this.props.wysiwyg.odooEditor.execCommand('applyColor', '', 'backgroundColor');

        this._colorpaletteApply(cssProperty, params);

        this.props.wysiwyg.odooEditor.historyStep();
        this._updateOptionsUI();
    }
    /**
     * @private
     */
    _colorpaletteApply(cssProperty, params) {
        const prefix = this.PREFIXES[cssProperty];
        let color = params.color;
        const colorNames = this.colorpickers[cssProperty].colorNames;
        const colorClasses = prefix ? weUtils.computeColorClasses(colorNames, prefix) : [];
        const colorClass = `${prefix}${color}`;
        if (colorClasses.includes(colorClass)) {
            color = colorClass;
        } else if (colorNames.includes(color)) {
            // Store as color value.
            color = weUtils.getCSSVariableValue(color);
        }
        this.customColors[cssProperty] = color;
        this.applyLinkToDom(this._getData());
    }
    /**
     * Updates the label input with the DOM content of the link.
     *
     * @private
     */
    _updateLabelInput() {
        if (this.$el) {
            this.$el[0].querySelector('#o_link_dialog_label_input').value =
                weUtils.getLinkLabel(this.linkEl);
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickCheckbox(ev) {
        const $target = $(ev.target);
        $target.closest('we-button.o_we_checkbox_wrapper').toggleClass('active');
        if (ev.target.getAttribute("name") === "direct_download") {
            const el = ev.target.closest("we-button.o_we_checkbox_wrapper");
            const urlInputEl = this.$el[0].querySelector("#o_link_dialog_url_input");
            let href = urlInputEl.value.replace("&download=true", "");
            if (el.classList.contains("active")) {
                href += "&download=true";
                this.state.directDownload = true;
            }
            else {
                this.state.directDownload = false;
            }
            urlInputEl.value = href;
            this.state.url = href;
        } 
        this._adaptPreview();
    }
    _onPickSelectOption(ev) {
        const $target = $(ev.target);
        if ($target.closest('[name="link_border_style"]').length) {
            return;
        }
        const $select = $target.closest('we-select');
        $select.find('we-selection-items we-button').toggleClass('active', false);
        this._setSelectOption($target, true);
        this._updateOptionsUI();
        this._adaptPreview();
        // Reactivate the snippet to update the Button snippet editor's visibility
        // if the element type has changed (e.g., from button to link or vice versa).
        this.props.wysiwyg.snippetsMenuBus.trigger("ACTIVATE_SNIPPET", {
            $snippet: $(this.linkEl),
            onSuccess: () => { },
        });
    }
    /**
     * Sets the border width on the link.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeCustomBorderWidth(ev) {
        const value = ev.target.value;
        if (parseInt(value) >= 0) {
            this.$link.css('border-width', value + 'px');
        }
    }
    /**
     * Sets the border width on the link when enter is pressed.
     *
     * @private
     * @param {Event} ev
     */
    _onKeyPressCustomBorderWidth(ev) {
        if (ev.key === "Enter") {
            this._onChangeCustomBorderWidth(ev);
        }
    }
    /**
     * Sets the border style on the link.
     *
     * @private
     * @param {Event} ev
     */
    _onBorderStyleSelectOption(ev) {
        const value = ev.currentTarget.dataset.value;
        if (value) {
            this.$link.css('border-style', value);
            const $target = $(ev.currentTarget);
            const $activeBorderStyleToggler = $target.closest('we-select').find('we-toggler');
            $activeBorderStyleToggler.empty();
            $target.find('div').clone().appendTo($activeBorderStyleToggler);
            // Ensure only one option is active in the dropdown.
            $target.addClass('active');
            $target.siblings('we-button').removeClass("active");
            this.props.wysiwyg.odooEditor.historyStep();
        }
    }
    _checkDocumentState() {
        this.state.isDocument = false;
        this.state.directDownload = true;
        const url = this.state.url;
        if (url && url.startsWith("/web/content/")) {
            this.state.isDocument = !this.isLastAttachmentUrl;
            this.state.directDownload = url.includes("&download=true");
        }
    }
    /**
     * @override
     */
    __onURLInput() {
        super.__onURLInput(...arguments);
        this.props.wysiwyg.odooEditor.historyPauseSteps('_onURLInput');
        this._checkDocumentState();
        this._syncContent();
        this._adaptPreview();
        this.props.wysiwyg.odooEditor.historyUnpauseSteps('_onURLInput');
    }
    /**
     * Updates the DOM content of the link with the input value.
     *
     * @private
     * @param {Event} ev
     */
    _onLabelInput(ev) {
        const data = this._getData();
        if (!data) {
            return;
        }
        this._observer.disconnect();
        // Force update of link's content with new data using 'force: true'.
        // Without this, no update if input is same as original text.
        this._updateLinkContent(this.$link, data, {force: true});
        this._observer.observe(this.props.link, this._observerOptions);
    }
    /* If content is equal to previous URL, update it to match current URL.
     *
     * @private
     */
    _syncContent() {
        const previousUrl = this.linkEl.getAttribute('href');
        if (!previousUrl) {
            return;
        }
        const protocolLessPrevUrl = previousUrl.replace(/^https?:\/\/|^mailto:/i, '');
        const content = weUtils.getLinkLabel(this.linkEl);
        if (
            (content === previousUrl || content === protocolLessPrevUrl) &&
            this.linkComponentWrapperRef.el
        ) {
            const newUrl = this.linkComponentWrapperRef.el.querySelector('input[name="url"]').value;
            const protocolLessNewUrl = newUrl.replace(/^https?:\/\/|^mailto:/i, '')
            const newContent = content.replace(protocolLessPrevUrl, protocolLessNewUrl);
            this.linkComponentWrapperRef.el.querySelector('#o_link_dialog_label_input').value = newContent;
            this._onLabelInput();
        }
    }
}

export function shouldUnlink(link, colorCombinationClass) {
    return (!link.getAttribute("href") && !link.matches(".oe_unremovable")) && !colorCombinationClass && !isButton(link);
}
