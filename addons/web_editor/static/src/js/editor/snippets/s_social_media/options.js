/** @odoo-module **/

import fonts from 'wysiwyg.fonts';
import {generateHTMLId} from 'web_editor.utils';
import options from 'web_editor.snippets.options';
import {_t} from 'web.core';

const faRegx = new RegExp('\\b' + 'fa-' + '[^1-9][^ ]*[ ]?\\b');
export const SocialMedia = options.registry.SocialMedia = options.Class.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this._lastEntries = [];
        this._nodeToId = new Map();
        this._idToNode = new Map();
    },
    /**
     * @override
     */
    start() {
        this._sampleLink = this.$target[0].querySelector(':scope > a');
        // When the alert is clicked, focus the first media input in the editor.
        this.__onSetupBannerClick = this._onSetupBannerClick.bind(this);
        this.$target[0].addEventListener('click', this.__onSetupBannerClick);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async onBuilt() {
        for (const anchorEl of this.$target[0].querySelectorAll(':scope > a')) {
            const mediaName = this._getInternalMediaName(anchorEl.href);
            const medias = await this._getStickyMedias();
            // Delete social media without href or value in DB.
            if (!anchorEl.href || (mediaName && medias && !medias[mediaName])) {
                anchorEl.remove();
            }
        }
        this._normalizeNodes();
        // Ensure we do not drop a blank block.
        this._handleNoMediaAlert();
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target[0].removeEventListener('click', this.__onSetupBannerClick);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Applies the we-list on the target and rebuilds the social links.
     *
     * @see this.selectClass for parameters
     */
    async renderListItems(previewMode, widgetValue, params) {
        // The method _notifyCurrentState of ListUserValueWidget change the
        // type of the value. The following transform the value to their proper type.
        this._lastEntries = JSON.parse(widgetValue).map(entry => {
            if (typeof entry.notToggleable === "string") {
                entry.notToggleable = entry.notToggleable === "true" ? true : false;
            }
            if (typeof entry.undeletable === "string") {
                entry.undeletable = entry.undeletable === "true" ? true : false;
            }
            if (entry.media === "undefined") {
                entry.media = undefined;
            }
            return entry;
        });

        for (const [el, id] of this._nodeToId.entries()) {
            const entry = this._lastEntries.find(x => x.id === id);
            if (!entry || (!entry.undeletable && !el.parentElement)) {
                const id = this._nodeToId.get(el);
                el.remove();
                this._nodeToId.delete(el);
                this._idToNode.delete(id);
                this._lastEntries = this._lastEntries.filter(x=>x.id !== id);
            }
        }

        for (const entry of this._lastEntries) {
            let anchorEl = this._idToNode.get(entry.id);
            if (!entry.selected) {
                if (anchorEl && anchorEl.parentElement) {
                    this._nodeToId.delete(anchorEl);
                    this._idToNode.delete(entry.id);
                    anchorEl.remove();
                }
                continue;
            }

            // New entries could have been created through the ListUserValueWidget.
            if (!entry.id) {
                entry.id = generateHTMLId();
            }
            // Check if the url is valid.
            const url = entry.display_name;
            if (url && !/^(([a-zA-Z]+):|\/)/.test(url)) {
                // We permit every protocol (http:, https:, ftp:, mailto:,...).
                // If none is explicitly specified, we assume it is a https.
                entry.display_name = `https://${url}`;
            }
            if (!anchorEl) {
                const sampleLink = this.$target[0].querySelector(':scope > a') || this._sampleLink;
                if (!sampleLink) {
                    // Create a HTML element if no one already exist.
                    anchorEl = document.createElement('a');
                    anchorEl.setAttribute('target', '_blank');
                    const faEl = this._createIconElement();
                    anchorEl.appendChild(faEl);
                } else {
                    // Copy existing style if there is already another link.
                    anchorEl = sampleLink.cloneNode(true);
                    anchorEl.removeAttribute('title');
                    anchorEl.removeAttribute('data-original-title');
                    anchorEl.removeAttribute('aria-label');
                    this._removeFaClasses(anchorEl.querySelector('.fa'));
                }
                this._nodeToId.set(anchorEl, entry.id);
                this._idToNode.set(entry.id, anchorEl);
            }

            // Handle URL change for custom links.
            const href = anchorEl.getAttribute('href');
            if (href !== entry.display_name) {
                anchorEl.setAttribute('href', entry.display_name);
            }

            this._updateEntryAnchorEl(entry, anchorEl);
            // Place the link at the correct position
            this.$target[0].appendChild(anchorEl);
        }

        // Restore whitespaces around the links
        this.$target[0].normalize();
        this._normalizeNodes();
        this._handleNoMediaAlert();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName !== 'renderListItems') {
            return this._super(methodName, params);
        }
        for (const entry of this._lastEntries) {
            entry.selected = false;
        }

        const medias = await this._getStickyMedias();
        // Check the DOM to compute the state of the ListUserValueWidget.
        for (const el of this.$target[0].querySelectorAll(':scope > a')) {
            const media = this._getAnchorMediaName(el, Object.keys(medias));
            // Prevent having twice the same media being toggleable/undeletable
            delete medias[media];
            const id = this._nodeToId.get(el);
            const entry = id && this._lastEntries.find(x => x.id === id);
            const entryOption = {
                id: (entry && entry.id) || generateHTMLId(),
                display_name: await this._getDisplayName(el.getAttribute('href')),
                placeholder: `https://${media || 'example'}.com/yourPage`,
                undeletable: !!media,
                notToggleable: !media,
                media: media,
                selected: true,
            };
            if (entry) {
                Object.assign(entry, entryOption);
            } else {
                entryOption.selected = true;
                this._lastEntries.push(entryOption);
            }
            this._nodeToId.set(el, entryOption.id);
            this._idToNode.set(entryOption.id, el);
        };

        // Adds the DB social media links that are not in the DOM.
        for (const [mediaName, mediaUrl] of await Object.entries(medias)) {
            const entry = this._lastEntries.find(x => x.media === mediaName);
            if (!entry) {
                this._lastEntries.push({
                    id: generateHTMLId(),
                    display_name: mediaUrl,
                    placeholder: `https://${mediaName}.com/yourPage`,
                    undeletable: true,
                    notToggleable: false,
                    selected: false,
                    media: mediaName,
                });
            }
        }

        return JSON.stringify(this._lastEntries);
    },
    /**
     * Finds the social network for the given entry.
     *
     * @param {String} entry
     * @return {String | undefined} The social network to which the url leads to.
     */
    _getEntryMediaIcon(entry) {
        if (entry.media) {
            return entry.media;
        }
        const url = entry.display_name;
        if (!this._isValidURL(url)) {
            return;
        }
        const media = this._getSupportedSocialMedia(url);
        if (media) {
            return media;
        }
        // Check if an icon matches the URL domain
        try {
            const domain = new URL(url).hostname.split('.').slice(-2)[0];
            fonts.computeFonts();
            const iconNames = fonts.fontIcons[0].alias;
            const exactIcon = iconNames.find(el => el === `fa-${domain}`);
            return (exactIcon || iconNames.find(el => el.includes(domain))).split('fa-').pop();
        } catch {
            return false;
        }
    },
    /**
     * Finds the supported social network for the given url.
     *
     * @param {String} url
     * @return {String} The social network to which the url leads to.
     */
    _getSupportedSocialMedia(url) {
        const supportedSocialMedia = [
            ['facebook', /^(https?:\/\/)(www\.)?(facebook|fb|m\.facebook)\.(com|me).*$/],
            ['twitter', /^(https?:\/\/)((www\.)?twitter\.com).*$/],
            ['youtube', /^(https?:\/\/)(www\.)?(youtube.com|youtu.be).*$/],
            ['instagram', /^(https?:\/\/)(www\.)?(instagram.com|instagr.am|instagr.com).*$/],
            ['linkedin', /^(https?:\/\/)((www\.)?linkedin\.com).*$/],
            ['github', /^(https?:\/\/)((www\.)?github\.com).*$/],
        ];
        for (const [socialMedia, regex] of supportedSocialMedia) {
            if (regex.test(url)) {
                return socialMedia;
            }
        }
    },
    /**
     * Adds a warning banner to alert that there are no social networks.
     */
    _handleNoMediaAlert() {
        const alertEl = this.$target[0].querySelector('div.css_non_editable_mode_hidden');
        if (this.$target[0].querySelector(':scope > a:not(.d-none)')) {
            if (alertEl) {
                alertEl.remove();
            }
        } else {
            if (!alertEl) {
                // Create the alert banner.
                const divEl = document.createElement('div');
                const classes = ['alert', 'alert-info', 'css_non_editable_mode_hidden', 'text-center'];
                divEl.classList.add(...classes);
                const spanEl = document.createElement('span');
                spanEl.textContent = _t("Click here to setup your social networks");
                this.$target[0].appendChild(divEl).append(spanEl);
            }
        }
    },
    /**
     * @param  {String} str
     * @returns {boolean} is the string a valid URL.
     */
    _isValidURL(str) {
        let url;
        try {
            url = new URL(str);
        } catch {
            return false;
        }
        return url.protocol.startsWith('http');
    },
    /**
     * @param {object} entry
     * @param {HTMLElement} anchorEl
     */
    _updateEntryAnchorEl(entry, anchorEl) {
        const href = this._getEntrySavedUrl(entry);
        anchorEl.href = href;
        const socialRegx = new RegExp('\\b' + 's_social_media_' + '[^1-9][^ ]*[ ]?\\b');
        anchorEl.className = anchorEl.className.replace(socialRegx, '');
        const icon = this._getEntryMediaIcon(entry);
        if (entry.media && icon) {
            anchorEl.classList.add(`s_social_media_${icon}`);
        }

        const faEl = anchorEl.querySelector('.fa');
        const faClass = this._getEntryMediaIcon(entry);
        if (faEl && (entry.media || faClass || !faEl.className.match(faRegx))) {
            this._removeFaClasses(faEl);
            faEl.classList.add(`fa-${faClass || 'pencil'}`);
        }
    },
    /**
     * Remove every fa classes except fa-x sizes of `faEl`.
     *
     * @param {HTMLElement} faEl A fa icon element
     */
    _removeFaClasses(faEl) {
        faEl.className = faEl.className.replace(faRegx, '');
    },

    /**
     * Get a dictionnary of media with the default url as the values that will
     * be unremovable and togglable in the ListUserValueWidget.
     */
    _getStickyMedias() {
        return {
            facebook: 'https://www.facebook.com/Odoo',
            twitter: 'https://twitter.com/Odoo',
            linkedin: 'https://www.linkedin.com/company/odoo',
            youtube: 'https://www.youtube.com/user/OpenERPonline',
            instagram: 'https://www.instagram.com/explore/tags/odoo/',
            github: 'https://github.com/odoo',
        }
    },
    /**
     * Get a media name from an anchor element.
     *
     * @param {HTMLElement} anchorEl
     * @param {object[]} availableMedias
     */
    _getAnchorMediaName(anchorEl, availableMedias) {
        const media = this._getInternalMediaName(anchorEl.href);
        if (!media) {
            const faEl = anchorEl.querySelector('.fa');
            for (const mediaName of availableMedias) {
                if (faEl.classList.contains(`fa-${mediaName}`)) {
                    return mediaName;
                }
            }
        }
        return (availableMedias.includes(media) && media) || undefined;
    },
    /**
     * Get media name from an url.
     *
     * @param {string} url
     * @returns {string|undefined}
     */
    _getInternalMediaName(url) {
        return this._getSupportedSocialMedia(url);
    },
    /**
     * Get the display name from the media name or the url.
     */
    _getDisplayName(url) {
        return url;
    },
    /**
     * Get the url to set in the anchor element for an entry.
     *
     * @return {string}
     */
    _getEntrySavedUrl(entry) {
        return entry.display_name;
    },
    /**
     * Create a icon element
     * @return {HTMLElement}
     */
    _createIconElement() {
        const faEl = document.createElement('span');
        faEl.classList.add('fa', 'fa-pencil');
        return faEl;
    },
    _normalizeNodes() {
        for (const node of [...this.$target[0].childNodes]) {
            if (node.tagName !== 'A') {
                node.remove();
            }
        }
        for (const node of [...this.$target[0].childNodes].slice(0, -1)) {
            const textNode = document.createTextNode(" ");
            node.after(textNode);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onSetupBannerClick(ev) {
        if (ev.target.closest('div.css_non_editable_mode_hidden')) {
            // TODO if the options are not already instantiated, this won't
            // work of course
            this._requestUserValueWidgets('social_media_list')[0].focus();
        }
    },
});
