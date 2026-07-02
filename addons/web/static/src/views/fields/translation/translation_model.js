import { computed, config, onWillStart, Plugin, Resource, signal, types } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

const LOCAL_STORAGE_PREFERRED_LANG_KEY = "web.translate.field.preferred.lang.to";
const _refreshStorage = signal(0);
const langStorage = computed(
    () => {
        _refreshStorage();
        return browser.localStorage.getItem(LOCAL_STORAGE_PREFERRED_LANG_KEY);
    },
    {
        set: (lang) => {
            browser.localStorage.setItem(LOCAL_STORAGE_PREFERRED_LANG_KEY, lang);
            _refreshStorage.set(_refreshStorage() + 1);
        },
    }
);

const userContext = computed(() => user.context);
const userLang = computed(() => userContext().lang);
const globalLang = computed(() => [langStorage(), userLang()].filter(Boolean)[0]);

export class TranslateModel extends Plugin {
    on_saved = new Resource();
    get_translation_key = new Resource();
    terms_menu_items = new Resource();

    // Config
    field = config(
        "field",
        types.signal({
            type: types.string(),
            name: types.string(),
        })
    );
    resModel = config("resModel", types.signal());
    resId = config("resId", types.signal());
    userLang = userLang();

    translateMode = signal(null);

    // Languages
    baseLang = signal(null);
    _currentLang = signal(null);
    currentLang = computed(() => this._currentLang() || globalLang());
    fallbackLang = computed(() => {
        if ("en_US" in this.languages()) {
            return "en_US";
        }
        return Object.keys(this.valuesSet())[0];
    });
    languages = signal.Object({});

    canSave = computed(() => Object.keys(this.changesSet()).length);

    // Data and changes in case the translations are whole
    terms = signal.Array([]);
    termsMap = computed(() => Object.fromEntries(this.terms().map((l) => [l.lang, l.value])));
    termsByLang = computed(() => Object.fromEntries(this.terms().map((l) => [l.lang, l])));
    _fullChanges = signal.Object({});

    // Data and changes when translations are in block (xml_translate)
    xmlValues = signal.Object({});
    _hashChanges = signal.Object({});

    valuesSet = computed(() =>
        this.translateMode() === "xml" ? this.xmlValues() : this.termsMap()
    );
    changesSet = computed(() =>
        this.translateMode() === "xml" ? this._hashChanges() : this._fullChanges()
    );

    setup() {
        this.get_translation_key.use((attributes) => attributes["data-oe-translation-source-sha"]);

        this.terms_menu_items.use((lang, term) => {
            if (this.translateMode() !== "xml" && lang === this.userLang) {
                return {
                    attrs: {
                        name: "apply_to_all",
                    },
                    label: _t("Apply to all languages"),
                    onSelected: () => this.applyToAll(lang),
                };
            }
        });

        onWillStart(() => this.load({ lang: globalLang }));
    }

    get fieldType() {
        return this.field().type;
    }

    // CRUD
    _load({ resModel, resId, field, lang, context }) {
        return rpc("/web/translations/get_translation_for_field", {
            res_model: resModel(),
            res_id: resId(),
            field_name: field().name,
            target_lang: lang(),
            context: context(),
        });
    }

    async load(params = {}) {
        const data = await this._load({
            resModel: this.resModel,
            resId: this.resId,
            field: this.field,
            context: userContext,
            ...params,
        });
        this._selfUpdate(data);
    }

    async save(params = {}) {
        let changes = params.changes;
        if (!changes) {
            changes = this._getChanges();
        }
        const data = await this._save({
            resModel: this.resModel,
            resId: this.resId,
            field: this.field,
            context: userContext,
            ...params,
            changes,
        });
        if (data) {
            this._selfUpdate(data);
        }
        for (const fn of this.on_saved.items()) {
            fn();
        }
    }

    _save({ resModel, resId, field, lang, context, changes }) {
        return rpc("/web/translations/save_translation_for_field", {
            res_model: resModel(),
            res_id: resId(),
            field_name: field().name,
            changes,
            target_lang: lang?.(),
            context: context(),
        });
    }

    _computeTranslationMode(mode) {
        return mode === "structured_html" ? "xml" : mode;
    }

    _selfUpdate(data = {}) {
        const { languages, translation_mode, terms, xml_values } = data;

        if (languages) {
            this.languages.set(languages);
        }
        this.translateMode.set(
            this._computeTranslationMode(translation_mode ?? this.translateMode)
        );
        if (xml_values) {
            Object.assign(this.xmlValues(), xml_values);
        }
        if (terms) {
            this.terms.set(terms);
        }

        const codes = Object.keys(this.valuesSet());
        let current = this.currentLang();
        if (!(current in codes)) {
            current = codes[0];
        }

        if (this.translateMode() === "html") {
            const codesIt = codes[Symbol.iterator]();
            while (current === this.userLang) {
                const { value, done } = codesIt.next();
                if (done) {
                    break;
                }
                current = value;
            }
        }
        this._currentLang.set(current || this.currentLang());

        if (this.translateMode() === "xml") {
            const _baseLang = Object.values(this.languages()).find((l) => l.is_base);
            this.baseLang.set(_baseLang?.code);
        }
    }

    _getChanges() {
        const changes = { ...this.changesSet() };
        if (this.translateMode() !== "xml") {
            for (const lang in changes) {
                if (changes[lang].description === lang) {
                    changes[lang] = this.getValue(lang);
                } else if (changes[lang].description) {
                    changes[lang] = null;
                }
            }
        }
        return changes;
    }
    // END CRUD

    // Whole translations
    getValue(lang = null) {
        lang ??= this.currentLang();
        const change = this._fullChanges()[lang];
        if (change?.description && change.description !== lang) {
            return this.getValue(change.description);
        }
        return change && !change.description
            ? change
            : this.termsMap()[lang] ||
                  (this.fallbackLang() && lang !== this.fallbackLang()
                      ? this.getValue(this.fallbackLang())
                      : false);
    }

    setValue(lang, value) {
        value = value || Symbol.for("en_US");
        this._fullChanges()[lang] = value;
    }

    // Block translations (xml_translate)
    getTranslationKey(obj) {
        // take the last function that can compute a key from an Object
        const item = this.get_translation_key.items().at(-1);
        return item?.(obj);
    }

    getHashChange(lang = null, key) {
        lang ??= this.currentLang();
        return this._hashChanges()[lang]?.[key];
    }

    setHashChange(lang = null, key, value) {
        lang ??= this.currentLang();
        const changes = this._hashChanges();
        changes[lang] ??= {};
        changes[lang][key] = value;
    }

    // Other features
    getLang(lang = null) {
        lang ??= this.currentLang();
        return this.languages()[lang];
    }

    applyToAll(srcLang) {
        const changes = this._fullChanges();
        for (const lang in this.languages()) {
            if (srcLang === lang) {
                changes[lang] = changes[lang] ?? Symbol.for(srcLang);
            } else {
                changes[lang] = Symbol.for(srcLang);
            }
        }
    }

    langStatus(lang) {
        const changes = this.changesSet();
        if (!(lang in changes)) {
            return "no_change";
        }
        return changes[lang]?.description ? "reset" : "changed";
    }

    async changeLang(lang) {
        const values = this.valuesSet();
        if (values[lang] === undefined) {
            await this.load({ lang: () => lang });
        }
        this._currentLang.set(lang);
        langStorage.set(lang);
    }

    getTitle() {}

    getLangMenuItems(lang) {
        const term = this.termsByLang()[lang];
        const items = this.terms_menu_items.items();
        return items.map((i) => i(lang, term)).filter(Boolean);
    }
}
