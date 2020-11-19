odoo.define('pad.pad', function (require) {
    "use strict";

    const AbstractField = require('web.AbstractFieldOwl');
    const fieldRegistry = require('web.field_registry_owl');
    const { onMounted, onPatched } = owl.hooks;

    class FieldPad extends AbstractField {
        constructor(...args) {
            super(...args);
            this.content = "";

            onMounted(() => this._updatePad());
            onPatched(() => this._updatePad());
        }
        /**
         * @override
         */
        async willStart() {
            if (this.isPadConfigured === undefined) {
                const result = await this.env.services.rpc({
                    method: 'pad_is_configured',
                    model: this.model,
                });
                // we write on the prototype to share the information between
                // all pad widgets instances, across all actions
                FieldPad.prototype.isPadConfigured = result;
            }
        }

        mounted() {
            if (!this.isPadConfigured) {
                this.el.querySelector('.oe_unconfigured').classList.remove("d-none");
                this.el.querySelector('.oe_configured').classList.add("d-none");
                return Promise.resolve;
            }
            if (this.mode === 'edit' && this.value && this.value.startsWith('http')) {
                this.url = this.value;
                // please close your eyes and look elsewhere...
                // Since the pad value (the url) will not change during the edition
                // process, we have a problem: the description field will not be
                // proper!this.isPadConfiguredly updated.  We need to explicitely write the value each
                // time someone edit the record in order to force the server to read
                // the updated value of the pad and put it in the description field.
                //
                // However, the basic model optimizes away the changes if they are
                // not really different from the current value. So, we need to
                // either add special configuration options to the basic model, or
                // to trick him into accepting the same value as being different...
                // Guess what we decided...
                const url = {};
                url.toJSON = _.constant(this.url);
                this._setValue(url, {doNotSetDirty: true});
            }
        }

        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        get isSet() {
            return true;
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * If we had to generate an url, we wait for the generation to be completed,
         * so the current record will be associated with the correct pad url.
         *
         * @override
         */
        commitChanges() {
            return this.urlDef;
        }

        /**
         * This method will update pad based on current mode
         *
         * @private
         */
        _updatePad() {
            if (this.mode === 'edit') {
                if (this.url) {
                    // here, we have a valid url, so we can simply display an iframe
                    // with the correct src attribute
                    const userName = encodeURIComponent(this.env.session.name);
                    const url = this.url + '?showChat=false&userName=' + userName;
                    const content = '<iframe width="100%" height="100%" frameborder="0" src="' + url + '"></iframe>';
                    this.el.querySelector('.oe_pad_content').innerHTML = content;
                } else if (this.value) {
                    // it looks like the field does not contain a valid url, so we just
                    // display it (it cannot be edited in that case)
                    this.el.querySelector('.oe_pad_content').innerText = this.value;
                } else {
                    // It is totally discouraged to have a render method that does
                    // non-rendering work, especially since the work in question
                    // involves doing RPCs and changing the value of the field.
                    // However, this is kind of necessary in this case, because the
                    // value of the field is actually only the url of the pad. The
                    // actual content will be loaded in an iframe.  We could do this
                    // work in the basic model, but the basic model does not know that
                    // this widget is in edit or readonly, and we really do not want to
                    // create a pad url everytime a task without a pad is viewed.
                    this.urlDef = this.env.services.rpc({
                        method: 'pad_generate_url',
                        model: this.model,
                        context: {
                            model: this.model,
                            field_name: this.name,
                            object_id: this.resId
                        },
                    }, {
                        shadow: true
                    }).then((result) => {
                        // We need to write the url of the pad to trigger
                        // the write function which updates the actual value
                        // of the field to the value of the pad content
                        this.url = result.url;
                        this._setValue(result.url, {doNotSetDirty: true});
                    });
                }
            } else {
                if (this.value && this.value.startsWith('http')) {
                    const padContent = this.el.querySelector('.oe_pad_content');
                    padContent.classList.add('.oe_pad_loading');
                    padContent.textContent = this.env._t("Loading");
                    this.env.services.rpc({
                        method: 'pad_get_content',
                        model: this.model,
                        args: [this.value]
                    }, {
                        shadow: true
                    }).then((data) => {
                        padContent.classList.remove('oe_pad_loading');
                        padContent.innerHTML = '<div class="oe_pad_readonly"><div>';
                        this.el.querySelector('.oe_pad_readonly').innerHTML = data;
                    }).guardedCatch(function () {
                        padContent.innerText = this.env._t('Unable to load pad');
                    });
                } else {
                    const padContent = this.el.querySelector('.oe_pad_content');
                    padContent.classList.add('oe_pad_loading');
                    padContent.innerText = "This pad will be initialized on first edit";
                }
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        async _onToggleFullScreen() {
            this.el.classList.toggle('oe_pad_fullscreen');
            this.el.classList.toggle('mb0');
            this.el.querySelector('.oe_pad_switch').classList.toggle('fa-expand');
            this.el.querySelector('.oe_pad_switch').classList.toggle('fa-compress');
            // find parent node until we get element with o_touch_device class
            let el = this.el;
            while (el && el.parentNode) {
                el = el.parentNode;
                if (el.classList && el.classList.contains('o_touch_device')) {
                    return el.classList.toggle('o_scroll_hidden');
                }
            }
        }
    }

    FieldPad.template = "FieldPad";
    fieldRegistry.add('pad', FieldPad);

    return FieldPad;

});
