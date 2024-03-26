/** @odoo-module **/

import { onMounted, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Link } from "./link";

export class LinkDialog extends Link {
    static components = { Dialog };
    static template = 'web_editor.LinkDialog';
    static props = {
        ...Link.props,
        focusField: { type: String, optional: true },
        close: { type: Function },
        onClose: { type: Function },
        onSave: { type: Function },
    };
    inputTextRef = useRef('inputText');
    inputUrlRef = useRef('inputUrl');

    setup() {
        super.setup();
        onMounted(() => {
            this.$el.find('[name="link_style_color"]').on('change', this._onTypeChange.bind(this));
            this.$el.find('input[name="label"]').on('input', this._adaptPreview.bind(this));
            const el = this.props.focusField === 'url' ? this.inputUrlRef.el : this.inputTextRef.el;
            el.focus();
        });
        this.env.dialogData.close = () => this.onDiscard();
    }

    /**
     * @override
     */
    start() {
        super.start();
        this.buttonOptsCollapseEl = this.linkComponentWrapperRef.el.querySelector('#o_link_dialog_button_opts_collapse');
        this.$styleInputs = this.$el.find('input.link-style');
        this.$styleInputs.prop('checked', false).filter('[value=""]').prop('checked', true);
        if (this.initialNewWindow) {
            this.$el.find('we-button.o_we_checkbox_wrapper').toggleClass('active', true);
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    onSave(ev) {
        ev.preventDefault();
        var data = this._getData();
        if (data === null) {
            var $url = this.$el.find('input[name="url"]');
            $url.closest('.o_url_input').addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
            $url.focus();
            return;
        }
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        var allBtnTypes = /(^|[ ])(btn-secondary|btn-success|btn-primary|btn-info|btn-warning|btn-danger)([ ]|$)/gi;
        data.classes = data.classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, '');
        if (data.classes.replace(allBtnTypes, ' ')) {
            data.style = {
                'background-color': '',
                'color': '',
            };
        }
        data.linkDialog = this;
        this.props.close();
        this.props.onSave(data);
    }

    onDiscard() {
        this.props.onClose();
        this.props.close();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _adaptPreview() {
        var data = this._getData();
        if (data === null) {
            return;
        }
        const attrs = {
            target: '_blank',
            href: data.url && data.url.length ? data.url : '#',
            class: `${data.classes.replace(/float-\w+/, '')} o_btn_preview`,
        };

        const $linkPreview = this.$el.find("#link-preview");
        $linkPreview.attr(attrs);
        this._updateLinkContent($linkPreview, data, { force: true });
    }
    /**
     * @override
     */
    _doStripDomain() {
        return this.$el.find('#o_link_dialog_url_strip_domain').prop('checked');
    }
    /**
     * @override
     */
    _getIsNewWindowFormRow() {
        return this.$el.find('input[name="is_new_window"]').closest('.row');
    }
    /**
     * @override
     */
    _getLinkOptions() {
        const options = [
            'select[name="link_style_color"] > option',
            'select[name="link_style_size"] > option',
            'select[name="link_style_shape"] > option',
        ];
        return this.$el.find(options.join(','));
    }
    /**
     * @override
     */
    _getLinkShape() {
        return this.$el.find('select[name="link_style_shape"]').val() || '';
    }
    /**
     * @override
     */
    _getLinkSize() {
        return this.$el.find('select[name="link_style_size"]').val() || '';
    }
    /**
     * @override
     */
    _getLinkType() {
        return this.$el.find('select[name="link_style_color"]').val() || '';
    }
    /**
     * @override
     */
    _isNewWindow(url) {
        if (this.props.forceNewWindow) {
            return this._isFromAnotherHostName(url);
        } else {
            return this.$el.find('input[name="is_new_window"]').prop('checked');
        }
    }
    /**
     * @override
     */
    _setSelectOption($option, active) {
        if ($option.is("input")) {
            $option.prop("checked", active);
        } else if (active) {
            $option.parent().find('option').removeAttr('selected').removeProp('selected');
            $option.parent().val($option.val());
            $option.attr('selected', 'selected').prop('selected', 'selected');
        }
    }
    /**
     * @override
     */
    _updateOptionsUI() {
        const el = this.linkComponentWrapperRef.el.querySelector('[name="link_style_color"] option:checked');
        $(this.buttonOptsCollapseEl).collapse(el && el.value ? 'show' : 'hide');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onTypeChange() {
        this._updateOptionsUI();
    }
    /**
     * @override
     */
    _onURLInput() {
        this.$el.find('#o_link_dialog_url_input').closest('.o_url_input').removeClass('o_has_error').find('.form-control, .form-select').removeClass('is-invalid');
        this._adaptPreview();
    }
}
