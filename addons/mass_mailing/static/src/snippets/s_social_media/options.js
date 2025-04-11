import fonts from '@web_editor/js/wysiwyg/fonts';
import weUtils from '@web_editor/js/common/utils';
import options from '@web_editor/js/editor/snippets.options';
import { _t } from "@web/core/l10n/translation";
import { ICON_SELECTOR } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

let dbSocialValues;
let dbSocialValuesProm;
let companyId = 1;
let updatedListItems;

const clearDbSocialValuesCache = () => {
    dbSocialValuesProm = undefined;
    dbSocialValues = undefined;
};

const getDbSocialValuesCache = () => dbSocialValues;

options.registry.SocialMedia = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.action = this.bindService("action");
        this.currentCompanyId = companyId;
    },

    start() {
        this.__onSetupBannerClick = this._onSetupBannerClick.bind(this);
        this.$target[0].addEventListener('click', this.__onSetupBannerClick);
        this.entriesNotInDom = [];

        const classlist = this.$target[0].classList;
        for (let className of classlist) {
            if (className.startsWith("o_company_")) {
                companyId = parseInt(className.split("_").pop());
            }
        }
        this.default_sort = companyId;
        updatedListItems = true;

        return this._super(...arguments);
    },

    async onBuilt() {
        await this._fetchSocialMedia(companyId);
        this._initializeSocialMediaLinks();
        this._handleNoMediaAlert();
    },

    destroy() {
        this._super(...arguments);
        this.$target[0].removeEventListener('click', this.__onSetupBannerClick);
    },

    setDefaultSort(previewMode, widgetValue) {
        this.default_sort = widgetValue;
        updatedListItems = false;
        companyId = parseInt(widgetValue);
        this._fetchSocialMedia(companyId);
    },

    redirectToCompany() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.company",
            res_id: companyId,
            views: [[false, "form"]],
        });
    },
    /**
     * Applies the we-list on the target and rebuilds the social links.
     *
     * @see this.selectClass for parameters
     */
    async renderListItems(previewMode, widgetValue) {
        const entries = JSON.parse(widgetValue);
        const anchorEls = this.$target[0].querySelectorAll(':scope > a');
        const anchorsToRemoveEls = [];
        this.entriesNotInDom = [];

        // Remove anchors not present in entries
        for (let i = 0; i < anchorEls.length; i++) {
            if (!entries.find(entry => parseInt(entry.domPosition) === i)) {
                anchorsToRemoveEls.push(anchorEls[i]);
            }
        }
        anchorsToRemoveEls.forEach(el => el.remove());
        // Iterate over the entries to process each one
        for (let listPosition = 0; listPosition < entries.length; listPosition++) {
            const entry = entries[listPosition];
            let anchorEl = anchorEls[entry.domPosition];
            const isDbField = Boolean(entry.media);

            if (isDbField) {
                dbSocialValues[`social_${entry.media}`] = entry.display_name;
            }

            if (entry.selected) {
                if (!anchorEl) {
                    if (anchorEls.length === 0) {
                        // Create an HTML element if none exists
                        anchorEl = document.createElement('a');
                        anchorEl.setAttribute('target', '_blank');
                        const iEl = document.createElement('i');
                        iEl.classList.add('fa', 'rounded-circle', 'shadow-sm', 'o_editable_media');
                        anchorEl.appendChild(iEl);
                    } else {
                        // Clone existing style if another link is present
                        anchorEl = this.$target[0].querySelector(':scope > a').cloneNode(true);
                        this._removeSocialMediaClasses(anchorEl);
                    }
                }
                this._updateAnchorElement(anchorEl, entry);
            } else {
                if (anchorEl) {
                    delete entry.domPosition;
                    anchorEl.remove();
                }
                entry.listPosition = listPosition;
                this.entriesNotInDom.push(entry);
                continue;
            }

            if (!isDbField) {
                // Handle URL change for custom links
                const href = anchorEl.getAttribute('href');
                if (href !== entry.display_name) {
                    let socialMedia = null;
                    if (this._isValidURL(entry.display_name)) {
                        socialMedia = this._findRelevantSocialMedia(entry.display_name);
                        if (socialMedia) {
                            const iEl = anchorEl.querySelector(ICON_SELECTOR);
                            this._removeSocialMediaClasses(anchorEl);
                            anchorEl.classList.add(`s_social_media_${socialMedia}`);
                            if (iEl) {
                                iEl.classList.add(`fa-${socialMedia}`);
                            }
                        }
                    }
                    anchorEl.setAttribute('href', entry.display_name);
                    this._setAriaLabelOfSocialNetwork(anchorEl, socialMedia, entry.display_name);
                }
            }

            this.$target[0].appendChild(anchorEl);
        }

        this._restoreWhitespace();
        this._handleNoMediaAlert();
    },
    /**
     * Sets ARIA label for social networks.
     * @param {HTMLElement} el 
     * @param {string} name 
     * @param {string} url 
     */
    _setAriaLabelOfSocialNetwork(el, name, url) {
        const ariaLabelsOfSocialNetworks = {
            "facebook": _t("Facebook"),
            "twitter": _t("X"),
            "linkedin": _t("LinkedIn"),
            "youtube": _t("YouTube"),
            "instagram": _t("Instagram"),
            "github": _t("GitHub"),
            "tiktok": _t("TikTok"),
        };

        let ariaLabel = ariaLabelsOfSocialNetworks[name];
        if (!ariaLabel) {
            try {
                ariaLabel = new URL(url).hostname.split('.').slice(-2)[0];
            } catch {
                ariaLabel = _t("Other social network");
            }
        }
        el.setAttribute("aria-label", ariaLabel);
    },

    async _computeWidgetState(methodName, params) {
        if (methodName === 'setDefaultSort') {
            return this.default_sort;
        }
        if (methodName !== 'renderListItems') {
            return this._super(methodName, params);
        }
        await this._fetchSocialMedia(companyId);
        const entries = this._computeEntries();
        return JSON.stringify(entries);
    },

    async _fetchSocialMedia(companyId) {
        dbSocialValuesProm = this.orm.read("res.company", [companyId], [
            "social_facebook",
            "social_twitter",
            "social_linkedin",
            "social_youtube",
            "social_instagram",
            "social_github",
            "social_tiktok",
        ]);
        const values = await dbSocialValuesProm;

        dbSocialValues = values[0];

        // Ensure dbSocialValues is properly formed
        if (!dbSocialValues) {
            throw new Error("dbSocialValues is undefined after ORM read");
        }

        delete dbSocialValues.id;

        // Compare if the company ID has changed
        if (this.currentCompanyId !== companyId) {
            this.currentCompanyId = companyId; // Update current company ID
            this._initializeSocialMediaLinks(); // Update links if company ID changed
        }
    },

    _initializeSocialMediaLinks() {
        const socialMedias = ["facebook", "twitter", "linkedin", "youtube", "instagram", "github", "tiktok"];
        socialMedias.forEach(media => {
            const href = dbSocialValues[`social_${media}`];
            if (href) {
                let anchorEl = this.$target[0].querySelector(`a.s_social_media_${media}`);
                if (!anchorEl) {
                    anchorEl = this._createAnchorElement();
                    anchorEl.classList.add(`s_social_media_${media}`);
                    this.$target[0].appendChild(anchorEl);
                }
                this._updateAnchorElement(anchorEl, {
                    display_name: href,
                    media: media,
                    selected: true,
                    domPosition: 0,
                });
            }
        });
    },

    _createAnchorElement() {
        const anchorEl = document.createElement('a');
        anchorEl.setAttribute('target', '_blank');
        const iEl = document.createElement('i');
        iEl.classList.add('fa', 'rounded-circle', 'shadow-sm', 'o_editable_media');
        anchorEl.appendChild(iEl);
        return anchorEl;
    },

    _updateAnchorElement(anchorEl, entry) {
        const isDbField = Boolean(entry.media);
        if (isDbField) {
            anchorEl.href = entry.display_name || dbSocialValues[`social_${entry.media}`];
            anchorEl.classList.add(`s_social_media_${entry.media}`);
        }
        const iEl = anchorEl.querySelector(ICON_SELECTOR);
        if (iEl) {
            iEl.classList.add(isDbField ? `fa-${entry.media}` : 'fa-pencil');
        }
    },

    _restoreWhitespace() {
        const finalLinkEls = this.$target[0].querySelectorAll(':scope > a');
        if (finalLinkEls.length) {
            finalLinkEls[0].previousSibling.textContent = '\n';
            finalLinkEls.forEach(linkEl => linkEl.after(document.createTextNode('\n')));
        }
    },

    _handleNoMediaAlert() {
        const alertEl = this.$target[0].querySelector('div.css_non_editable_mode_hidden');
        if (this.$target[0].querySelector(':scope > a:not(.d-none)')) {
            if (alertEl) {
                alertEl.remove();
            }
        } else if (!alertEl) {
            const divEl = document.createElement('div');
            divEl.classList.add('alert', 'alert-info', 'css_non_editable_mode_hidden', 'text-center');
            const spanEl = document.createElement('span');
            spanEl.textContent = _t("Click here to setup your social networks");
            this.$target[0].appendChild(divEl).append(spanEl);
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
     * Finds the social network for the given url.
     *
     * @param {String} url
     * @return {String} The social network to which the url leads to.
     */
    _findRelevantSocialMedia(url) {
        // Note that linkedin, twitter, github and tiktok will also work because
        // the url will match the good icon so we don't need a specific regex.
        const supportedSocialMedia = [
            ['facebook', /^(https?:\/\/)(www\.)?(facebook|fb|m\.facebook)\.(com|me).*$/],
            ['youtube', /^(https?:\/\/)(www\.)?(youtube.com|youtu.be).*$/],
            ['instagram', /^(https?:\/\/)(www\.)?(instagram.com|instagr.am|instagr.com).*$/],
        ];
        for (const [socialMedia, regex] of supportedSocialMedia) {
            if (regex.test(url)) {
                return socialMedia;
            }
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

    _onSetupBannerClick(ev) {
        if (ev.target.closest('div.css_non_editable_mode_hidden')) {
            this._requestUserValueWidgets('social_media_list')[0].focus();
        }
    },

    _computeEntries() {
        let listPosition = 0;
        let domPosition = 0;
        let entries = [...this.$target[0].querySelectorAll(':scope > a')].map(el => {
            const media = el.classList.value.match(/s_social_media_(\w+)/) ? el.classList.value.match(/s_social_media_(\w+)/)[1] : undefined;
            while (this.entriesNotInDom.find(entry => parseInt(entry.listPosition) === listPosition)) {
                listPosition++;
            }
            return {
                id: weUtils.generateHTMLId(),
                display_name: updatedListItems ? el.getAttribute('href') : dbSocialValues[`social_${media}`],
                placeholder: `https://${encodeURIComponent(media) || 'example'}.com/yourPage`,
                undeletable: !!media,
                notToggleable: !media,
                selected: true,
                listPosition: listPosition++,
                domPosition: domPosition++,
                media: media,
            };
        });

        for (let [media, link] of Object.entries(dbSocialValues)) {
            media = media.split('social_').pop();
            if(!this.$target[0].querySelector(`:scope > a.s_social_media_${media}`)){
                const entryNotInDom = this.entriesNotInDom.find(entry => entry.media === media);
                if (!entryNotInDom) {
                    this.entriesNotInDom.push({
                        id: weUtils.generateHTMLId(),
                        display_name: link,
                        placeholder: `https://${encodeURIComponent(media)}.com/yourPage`,
                        undeletable: true,
                        selected: false,
                        listPosition: listPosition++,
                        media: media,
                        notToggleable: false,
                    });
                } else {
                    entryNotInDom.display_name = link;
                    entryNotInDom.undeletable = true;
                    entryNotInDom.notToggleable = false;
                }
            }
        }
        // Sort the updated 'entries' array
        entries = entries.concat(this.entriesNotInDom);
        entries.sort((a, b) => a.listPosition - b.listPosition);
        return entries;
    },
    /**
     * Removes social media classes from the given element.
     *
     * @param  {HTMLElement} anchorEl
     */
    _removeSocialMediaClasses(anchorEl) {
        let regx = new RegExp('\\b' + 's_social_media_' + '[^1-9][^ ]*[ ]?\\b');
        anchorEl.className = anchorEl.className.replace(regx, '');
        const iEl = anchorEl.querySelector(ICON_SELECTOR);
        if (iEl) {
            regx = new RegExp('\\b' + 'fa-' + '[^1-9][^ ]*[ ]?\\b');
            // Remove every fa classes except fa-x sizes.
            iEl.className = iEl.className.replace(regx, '');
        }
    },
});

export default {
    SocialMedia: options.registry.SocialMedia,
    clearDbSocialValuesCache,
    getDbSocialValuesCache,
};
