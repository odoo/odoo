/** @odoo-module **/

import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { _t } from "@web/core/l10n/translation";
import { isVisible } from "@web/core/utils/ui";
import weUtils from "@web_editor/js/common/utils";
import {
    Component,
    onWillStart,
    onMounted,
    onWillUpdateProps,
    onWillDestroy,
    useState,
    useRef,
} from "@odoo/owl";
import { deduceURLfromText } from "@web_editor/js/editor/odoo-editor/src/utils/sanitize";

const { getDeepRange, getInSelection, EMAIL_REGEX, PHONE_REGEX } = OdooEditorLib;

/**
 * Allows to customize link content and style.
 */
export class Link extends Component {
    static props = {
        editable: true,
        link: true,
        needLabel: { type: Boolean, optional: true },
        forceNewWindow: { type: Boolean, optional: true },
        initialIsNewWindow: { type: Boolean, optional: true },
        shouldFocusUrl: { type: Boolean, optional: true },
    };
    static defaultProps = {
        needLabel: true,
        forceNewWindow: false,
        initialIsNewWindow: false,
        shouldFocusUrl: false,
    }
    linkComponentWrapperRef = useRef("linkComponentWrapper");
    colorsData = [
        {type: '', label: _t("Link"), btnPreview: 'link'},
        {type: 'primary', label: _t("Primary"), btnPreview: 'primary'},
        {type: 'secondary', label: _t("Secondary"), btnPreview: 'secondary'},
        {type: 'custom', label: _t("Custom"), btnPreview: 'custom'},
        // Note: by compatibility the dialog should be able to remove old
        // colors that were suggested like the BS status colors or the
        // alpha -> epsilon classes. This is currently done by removing
        // all btn-* classes anyway.
    ];
    setup() {
        this.state = useState({});
        // We need to wait for the `onMounted` changes to be done before
        // accessing `this.$el`.
        this.mountedPromise = new Promise(resolve => this.mountedResolve = resolve);

        onWillStart(() => this._updateState(this.props));
        let started = false;
        onMounted(async () => {
            if (started) {
                return;
            }
            started = true;
            if (!this.linkComponentWrapperRef.el) {
                // There is legacy code that can trigger the instantiation of the
                // link tool when it's parent component (the toolbar) is not in the
                // dom. If the parent element is not in the dom, owl will not return
                // `this.linkComponentWrapperRef.el` because of a check (see
                // `inOwnerDocument`).
                // Todo: this workaround should be removed when the snippet menu is
                // converted to owl.
                await new Promise(resolve => {
                    const observer = new MutationObserver(() => {
                        if (this.linkComponentWrapperRef.el) {
                            observer.disconnect();
                            resolve();
                        }
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            }
            this.$el = $(this.linkComponentWrapperRef.el);

            this.$el.find('input, select').on('input', this._onAnyChange.bind(this));
            this.$el.find('input, select').on('change', this._onAnyChange.bind(this));
            this.$el.find('[name="url"]').on('input', this.__onURLInput.bind(this));
            this.$el.find('[name="url"]').on('change', this._onURLInputChange.bind(this));

            await this.start();
            this.mountedResolve();
        });
        onWillUpdateProps(async (newProps) => {
            await this.mountedPromise;
            this._updateState(newProps);
            this.state.url = newProps.link.getAttribute('href') || '';
            this._setUrl({ shouldFocus: newProps.shouldFocusUrl });
        });
        onWillDestroy(() => {
            this.destroy();
        });
    }
    /**
     * @override
     */
    async start() {
        this._setSelectOptionFromLink();

        this._updateOptionsUI();

        this.$el[0].querySelector('#o_link_dialog_label_input').value = this.state.originalText;
        this._setUrl({ shouldFocus: this.props.shouldFocusUrl });
    }
    /**
     * @override
     */
    destroy () {
        if (this._savedURLInputOnDestroy) {
            this._adaptPreview();
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Apply the new link to the DOM (via `this.$link`).
     *
     * @param {object} data
     */
    applyLinkToDom(data) {
        // Some mass mailing template use <a class="btn btn-link"> instead of just a simple <a>.
        // And we need to keep the classes because the a.btn.btn-link have some special css rules.
        // Same thing for the "btn-success" class, this class cannot be added
        // by the options but we still have to ensure that it is not removed if
        // it exists in a template (e.g. "Newsletter Block" snippet).
        if (!data.classes.split(' ').includes('btn')) {
            for (const linkClass of this.toleratedClasses) {
                if (this.state.iniClassName && this.state.iniClassName.split(' ').includes(linkClass)) {
                    data.classes += " btn " + linkClass;
                }
            }
        }
        // When multiple buttons follow each other, they may break on 2 lines
        // or more on mobile, so they need a margin-bottom.
        if (data.classes.split(" ").includes("btn")) {
            const closestButtonSiblingEls = this._getDirectButtonSiblings(this.linkEl);
            if (closestButtonSiblingEls.length) {
                data.classes += " mb-2";
                closestButtonSiblingEls.forEach(btnEl => btnEl.classList.add("mb-2"));
            }
        }
        if (['btn-custom', 'btn-outline-custom', 'btn-fill-custom'].some(className =>
            data.classes.includes(className)
        )) {
            this.$link.css('color', data.classes.includes(data.customTextColor) ? '' : data.customTextColor);
            this.$link.css('background-color', data.classes.includes(data.customFill) || weUtils.isColorGradient(data.customFill) ? '' : data.customFill);
            this.$link.css('background-image', weUtils.isColorGradient(data.customFill) ? data.customFill : '');
            this.$link.css('border-width', data.customBorderWidth);
            this.$link.css('border-style', data.customBorderStyle);
            this.$link.css('border-color', data.customBorder);
        } else {
            this.$link.css('color', '');
            this.$link.css('background-color', '');
            this.$link.css('background-image', '');
            this.$link.css('border-width', '');
            this.$link.css('border-style', '');
            this.$link.css('border-color', '');
        }
        const attrs = Object.assign({}, this.state.oldAttributes, {
            href: data.url,
            target: data.isNewWindow ? '_blank' : '',
        });
        if (typeof data.classes === "string") {
            data.classes = data.classes.replace(/o_default_snippet_text/, '');
            attrs.class = `${data.classes}`;
        }
        if (data.rel) {
            attrs.rel = `${data.rel}`;
        }

        this.$link.attr(attrs);
        if (!this.$link.attr('target')) {
            this.$link[0].removeAttribute('target');
        }
        this._updateLinkContent(this.$link, data);
    }
    /**
     * Focuses the url input.
     */
    focusUrl() {
        const urlInput = this.$el[0].querySelector('input[name="url"]');
        urlInput.focus();
        urlInput.select();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _setUrl({ shouldFocus } = {}) {
        if (this.state.url) {
            const protocolLessUrl = this.state.url.replace(/^(https?|mailto|tel):(\/\/)?/i, '');
            this.$el.find('input[name="url"]').val(protocolLessUrl);
            this._onURLInput();
            this._savedURLInputOnDestroy = false;
        }
        if (shouldFocus) {
            this.focusUrl();
        }
    }
    /**
     * @private
     */
    _setSelectOptionFromLink() {
        for (const option of this._getLinkOptions()) {
            const $option = $(option);
            const value = $option.is('input') ? $option.val() : $option.data('value') || option.getAttribute('value');
            let active = false;
            if (value) {
                const subValues = value.split(',');
                let subActive = true;
                for (let subValue of subValues) {
                    const classPrefix = new RegExp('(^|btn-| |btn-outline-|btn-fill-)' + subValue);
                    subActive = subActive && classPrefix.test(this.state.iniClassName);
                }
                active = subActive;
            } else {
                active = !this.state.iniClassName
                         || this.toleratedClasses.some(val => this.state.iniClassName.split(' ').includes(val))
                         || !this.state.iniClassName.includes('btn-');
            }
            this._setSelectOption($option, active);
        }
    }
    /**
     * Abstract method: adapt the link to changes.
     *
     * @abstract
     * @private
     */
    _adaptPreview() {}
    /**
     * @private
     */
    _correctLink(url) {
        if (url.indexOf('tel:') === 0) {
            url = url.replace(/^tel:([0-9]+)$/, 'tel://$1');
        } else if (url && !url.startsWith('mailto:') && url.indexOf('://') === -1
                    && url[0] !== '/' && url[0] !== '#' && url.slice(0, 2) !== '${') {
            url = 'http://' + url;
        }
        return url;
    }
    _deduceUrl(text) {
        text = text.trim();
        if (/^(https?:|mailto:|tel:)/.test(text)) {
            // Text begins with a known protocol, accept it as valid URL.
            return text;
        } else {
            return deduceURLfromText(text, this.linkEl) || '';
        }
    }
    /**
     * Abstract method: return true if the URL should be stripped of its domain.
     *
     * @abstract
     * @private
     * @returns {boolean}
     */
    _doStripDomain() {}
    /**
     * Get the link's data (url, content and styles).
     *
     * @private
     * @returns {Object} {content: String, url: String, classes: String, isNewWindow: Boolean}
     */
    _getData() {
        var $url = this.$el.find('input[name="url"]');
        var url = $url.val();
        var content = this.$el.find('input[name="label"]').val() || url;

        if (!this.state.isButton && $url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        const type = this._getLinkType();
        const customTextColor = this._getLinkCustomTextColor();
        const customFill = this._getLinkCustomFill();
        const customBorder = this._getLinkCustomBorder();
        const customBorderWidth = this._getLinkCustomBorderWidth();
        const customBorderStyle = this._getLinkCustomBorderStyle();
        const customClasses = this._getLinkCustomClasses();
        const size = this._getLinkSize();
        const shape = this._getLinkShape();
        const shapes = shape ? shape.split(',') : [];
        const style = ['outline', 'fill'].includes(shapes[0]) ? `${shapes[0]}-` : '';
        const shapeClasses = shapes.slice(style ? 1 : 0).join(' ');
        const classes = (this.state.className || '') +
            (type ? (` btn btn-${style}${type}`) : '') +
            (type === 'custom' ? customClasses : '') +
            (type && shapeClasses ? (` ${shapeClasses}`) : '') +
            (type && size ? (' btn-' + size) : '');
        var isNewWindow = this._isNewWindow(url);
        var doStripDomain = this._doStripDomain();
        if (this.state.url.indexOf(location.origin) === 0 && doStripDomain) {
            this.state.url = this.state.url.slice(location.origin.length);
        }
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        return {
            content: content,
            url: this._correctLink(this.state.url),
            classes: classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, ''),
            customTextColor: customTextColor,
            customFill: customFill,
            customBorder: customBorder,
            customBorderWidth: customBorderWidth,
            customBorderStyle: customBorderStyle,
            oldAttributes: this.state.oldAttributes,
            isNewWindow: isNewWindow,
            doStripDomain: doStripDomain,
        };
    }
    /**
     * Return a list of all the descendants of a given element.
     *
     * @private
     * @param {Node} rootNode
     * @returns {Node[]}
     */
    _getDescendants(rootNode) {
        const nodes = [];
        for (const node of rootNode.childNodes) {
            nodes.push(node);
            nodes.push(...this._getDescendants(node));
        }
        return nodes;
    }
    /**
     * Abstract method: return a JQuery object containing the UI elements
     * holding the "Open in new window" option's row of the link.
     *
     * @abstract
     * @private
     * @returns {JQuery}
     */
    _getIsNewWindowFormRow() {}
    /**
     * Abstract method: return a JQuery object containing the UI elements
     * holding the styling options of the link (eg: color, size, shape).
     *
     * @abstract
     * @private
     * @returns {JQuery}
     */
    _getLinkOptions() {}
    /**
     * Abstract method: return the shape(s) to apply to the link (eg:
     * "outline", "rounded-circle", "outline,rounded-circle").
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkShape() {}
    /**
     * Abstract method: return the size to apply to the link (eg:
     * "sm", "lg").
     *
     * @private
     * @returns {string}
     */
    _getLinkSize() {}
    /**
     * Abstract method: return the type to apply to the link (eg:
     * "primary", "secondary").
     *
     * @private
     * @returns {string}
     */
    _getLinkType() {}
    /**
     * Returns the custom text color for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomTextColor() {}
    /**
     * Returns the custom border color for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomBorder() {}
    /**
     * Returns the custom border width for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomBorderWidth() {}
    /**
     * Returns the custom border style for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomBorderStyle() {}
    /**
     * Returns the custom fill color for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomFill() {}
    /**
     * Returns the custom text, fill and border color classes for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomClasses() {}
    /**
     * @private
     */
    _isFromAnotherHostName(url) {
        if (url.includes(window.location.hostname)) {
            return false;
        }
        try {
            const Url = URL || window.URL || window.webkitURL;
            const urlObj = url.startsWith('/') ? new Url(url, window.location.origin) : new Url(url);
            return (urlObj.origin !== window.location.origin);
        } catch {
            return true;
        }
    }
    /**
     * Abstract method: return true if the link should open in a new window.
     *
     * @abstract
     * @private
     * @returns {boolean}
     */
    _isNewWindow(url) {}
    /**
     * Abstract method: mark one or several options as active or inactive.
     *
     * @abstract
     * @private
     * @param {JQuery} $option
     * @param {boolean} [active]
     */
    _setSelectOption($option, active) {}
    /**
     * Update the link content.
     *
     * @private
     * @param {JQuery} $link
     * @param {object} linkInfos
     * @param {boolean} force
     */
    _updateLinkContent($link, linkInfos, { force = false } = {}) {
        if (force || (this.props.needLabel && (linkInfos.content !== this.state.originalText || linkInfos.url !== this.state.url))) {
            if (linkInfos.content === this.state.originalText) {
                $link.html(this.state.originalHTML.replaceAll('\u200B', '').replaceAll('\uFEFF', ''));
            } else if (linkInfos.content && linkInfos.content.length) {
                let contentWrapperEl = $link[0];
                const text = $link[0].innerText.replaceAll("\u200B", "").replaceAll("\uFEFF", "").trim();
                // Update the first not ZWS child element that has the same inner text
                // as the link with the new content while preserving child
                // elements within the link. (e.g. the link is bold and italic)
                let child;
                do {
                    contentWrapperEl = child || contentWrapperEl;
                    child = [...contentWrapperEl.children].find(
                        (element) => !element.hasAttribute("data-o-link-zws")
                    );
                } while (child?.innerText.replaceAll('\u200B', '').replaceAll('\uFEFF', '').trim() === text);
                contentWrapperEl.innerText = linkInfos.content;
            } else {
                $link.text(linkInfos.url);
            }
        }
    }
    /**
     * @abstract
     * @private
     */
    _updateOptionsUI() {}
    /**
     * Update the state.
     *
     * @private
     */
    async _updateState(props) {
        this.initialNewWindow = props.initialIsNewWindow;

        this.state.className = "";
        this.state.iniClassName = "";

        // The classes in the following array should not be in editable areas
        // but as there are still some (e.g. in the "newsletter block" snippet)
        // we make sure the options system works with them.
        this.toleratedClasses = ['btn-link', 'btn-success'];

        this.editable = props.editable;
        this.$editable = $(this.editable);

        if (props.link) {
            const range = document.createRange();
            range.selectNodeContents(props.link);
            this.state.range = range;
            this.$link = $(props.link);
            this.linkEl = props.link;
        }

        if (this.state.range) {
            this.$link = this.$link || $(OdooEditorLib.getInSelection(this.editable.ownerDocument, 'a'));
            this.linkEl = this.$link[0];
            this.state.iniClassName = this.$link.attr('class') || '';
            this.colorCombinationClass = false;
            let $node = this.$link;
            while ($node.length && !$node.is('body')) {
                const className = $node.attr('class') || '';
                const m = className.match(/\b(o_cc\d+)\b/g);
                if (m) {
                    this.colorCombinationClass = m[0];
                    break;
                }
                $node = $node.parent();
            }
            const linkNode = this.$link[0] || this.state.range.cloneContents();
            const linkText = weUtils.getLinkLabel(linkNode);
            this.state.originalText = linkText.replace(/[ \t\r\n]+/g, ' ');
            if (linkNode instanceof DocumentFragment) {
                this.state.originalHTML = $('<fakeEl>').append(linkNode).html();
            } else {
                this.state.originalHTML = linkNode.innerHTML;
            }
            this.state.url = this.$link.attr('href') || '';
        } else {
            this.state.originalText = this.state.originalText ? this.state.originalText.replace(/[ \t\r\n]+/g, ' ') : '';
        }

        this.state.url ||= this._deduceUrl(this.state.originalText, this.linkEl);

        if (this.linkEl) {
            this.initialNewWindow = this.initialNewWindow || this.linkEl.target === '_blank';
        }

        const classesToKeep = [
            'text-wrap', 'text-nowrap', 'text-start', 'text-center', 'text-end',
            'text-truncate',
        ];
        const keptClasses = this.state.iniClassName.split(' ').filter(className => classesToKeep.includes(className));
        const allBtnColorPrefixes = /(^|\s+)(bg|text|border)((-[a-z0-9_-]*)|\b)/gi;
        const allBtnClassSuffixes = /(^|\s+)btn((-[a-z0-9_-]*)|\b)/gi;
        const allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
        const btnMarginBottom = /(^|\s+)mb-2(\s+|$)/i;
        this.state.className = this.state.iniClassName
            .replace(allBtnColorPrefixes, ' ')
            .replace(allBtnClassSuffixes, ' ')
            .replace(allBtnShapes, " ")
            .replace(btnMarginBottom, " ");
        this.state.className += ' ' + keptClasses.join(' ');
        // 'o_submit' class will force anchor to be handled as a button in linkdialog.
        if (/(?:s_website_form_send|o_submit)/.test(this.state.className)) {
            this.state.isButton = true;
        }
    }
    /**
     * Returns an array of the buttons which are the closest non empty
     * previousSibling and/or nextSibling.
     *
     * @param {HTMLElement} el
     * @returns {HTMLElement[]}
     */
    _getDirectButtonSiblings(el) {
        return ["previous", "next"].reduce((buttonSiblingsEls, side) => {
            let siblingNode = el[`${side}Sibling`];
            while (siblingNode) {
                // If the node is an empty text node, or if it is a <br> tag or
                // an invisible element, it is not taken into account.
                if ((siblingNode.nodeType === 3 && !!siblingNode.textContent.match(/^\s*$/)) ||
                        (siblingNode.nodeType === 1 &&
                        (siblingNode.nodeName === "BR" || !isVisible(siblingNode)))) {
                    siblingNode = siblingNode[`${side}Sibling`];
                    continue;
                }
                if (siblingNode.nodeType === 1 && siblingNode.classList.contains("btn")) {
                    buttonSiblingsEls.push(siblingNode);
                }
                break;
            }
            return buttonSiblingsEls;
        }, []);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAnyChange(e) {
        if (!e.target.closest('input[type="text"]')) {
            this._adaptPreview();
        }
    }
    /**
     * @todo Adapt in master: in stable _onURLInput was both used as an event
     * handler responding to url input events + a private method called at the
     * widget lifecycle start. Originally both points were to update the link
     * tools/dialog UI. It was later wanted to actually update the DOM... but
     * should only be done in event handler part.
     *
     * This allows to differentiate the event handler part. In master, we should
     * take the opportunity to also update the `_updatePreview` concept which
     * updates the "preview" of the original link dialog but actually updates
     * the real DOM for the "new" link tools.
     *
     * @private
     */
    __onURLInput() {
        const inputValue = this.$el[0].querySelector('#o_link_dialog_url_input').value;
        this.state.url = this._deduceUrl(inputValue, this.linkEl) || inputValue;
        this._onURLInput(...arguments);
    }
    /**
     * @private
     */
    _onURLInput() {
        this._savedURLInputOnDestroy = true;
        var $linkUrlInput = this.$el.find('#o_link_dialog_url_input');
        let value = $linkUrlInput.val();
        let isLink = !EMAIL_REGEX.test(value) && !PHONE_REGEX.test(value);
        this._getIsNewWindowFormRow().toggleClass('d-none', !isLink);
        this.$el.find('.o_strip_domain').toggleClass('d-none', value.indexOf(window.location.origin) !== 0);
    }
    /**
     * @private
     */
    _onURLInputChange() {
        this._adaptPreview();
        this._savedURLInputOnDestroy = false;
    }
}

/**
 * Return the link element to edit. Create one from selection if none was
 * present in selection.
 *
 * @param {Node} [options.containerNode]
 * @param {Node} [options.startNode]
 * @returns {Object}
 */
export function getOrCreateLink({ containerNode, startNode } = {}) {
    if (startNode) {
        if ($(startNode).is('a')) {
            return { link: startNode, needLabel: false };
        } else {
            $(startNode).wrap('<a href="#"/>');
            return { link: startNode.parentElement, needLabel: false };
        }
    }

    const doc = containerNode && containerNode.ownerDocument || document;
    let needLabel = false;
    let link = getInSelection(doc, 'a');
    const $link = $(link);
    const range = getDeepRange(containerNode, {splitText: true, select: true, correctTripleClick: true});
    if (!range) {
        return {};
    }
    const isContained = containerNode.contains(range.startContainer) && containerNode.contains(range.endContainer);
    if (link && (!$link.has(range.startContainer).length || !$link.has(range.endContainer).length)) {
        // Expand the current link to include the whole selection.
        let before = link.previousSibling;
        while (before !== null && range.intersectsNode(before)) {
            link.insertBefore(before, link.firstChild);
            before = link.previousSibling;
        }
        let after = link.nextSibling;
        while (after !== null && range.intersectsNode(after)) {
            link.appendChild(after);
            after = link.nextSibling;
        }
    } else if (!link && isContained) {
        link = document.createElement('a');
        if (range.collapsed) {
            range.insertNode(link);
            needLabel = true;
        } else {
            link.appendChild(range.extractContents());
            range.insertNode(link);
        }
    }
    return { link, needLabel };
};
