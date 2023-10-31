odoo.define('website.newMenu', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var websiteNavbarData = require('website.navbar');
var wUtils = require('website.utils');
var tour = require('web_tour.tour');

const { registry } = require("@web/core/registry");

const {qweb, _t} = core;

var enableFlag = 'enable_new_content';

var NewContentMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        close_all_widgets: '_handleCloseDemand',
        new_page: '_createNewPage',
    }),
    events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.events || {}, {
        'click': '_onBackgroundClick',
        'click [data-module-id]': '_onModuleIdClick',
        'keydown': '_onBackgroundKeydown',
    }),
    // allow text to be customized with inheritance
    newContentText: {
        failed: _t('Failed to install "%s"'),
        installInProgress: _t("The installation of an App is already in progress."),
        installNeeded: _t('Do you want to install the "%s" App?'),
        installPleaseWait: _t('Installing "%s"'),
    },

    /**
     * Prepare the navigation and find the modules to install.
     * Move not installed module buttons after installed modules buttons,
     * but keep the original index to be able to move back the pending install
     * button at its final position, so the user can click at the same place.
     *
     * @override
     */
    start: function () {
        this.pendingInstall = false;
        this.$newContentMenuChoices = this.$('#o_new_content_menu_choices');

        var $modules = this.$newContentMenuChoices.find('.o_new_content_element');
        _.each($modules, function (el, index) {
            var $el = $(el);
            $el.data('original-index', index);
            if ($el.data('module-id')) {
                $el.appendTo($el.parent());
                $el.find('a i, a p').addClass('o_uninstalled_module');
            }
        });

        this.$firstLink = this.$newContentMenuChoices.find('a:eq(0)');
        this.$lastLink = this.$newContentMenuChoices.find('a:last');

        if ($.deparam.querystring()[enableFlag] !== undefined) {
            Object.keys(tour.tours).forEach(
                el => {
                    let element = tour.tours[el];
                    if (element.steps[0].trigger == '#new-content-menu > a'
                        && !element.steps[0].extra_trigger) {
                        element.steps[0].auto = true;
                    }
                }
            );
            this._showMenu();
        }
        this.$loader = $(qweb.render('website.new_content_loader'));
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new page to create, then creates it and
     * redirects the user to this new page.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewPage: function () {
        return wUtils.prompt({
            id: 'editor_new_page',
            window_title: _t("New Page"),
            input: _t("Page Title"),
            init: function () {
                var $group = this.$dialog.find('div.form-group');
                $group.removeClass('mb0');

                var $add = $('<div/>', {'class': 'form-group mb0 row'})
                            .append($('<span/>', {'class': 'offset-md-3 col-md-9 text-left'})
                                    .append(qweb.render('website.components.switch', {id: 'switch_addTo_menu', label: _t("Add to menu")})));
                $add.find('input').prop('checked', true);
                $group.after($add);
            }
        }).then(function (result) {
            // Remove any leading slash.
            const val = result.val.replace(/^\/*/, "");
            var $dialog = result.dialog;
            if (!val) {
                return;
            }
            var url = '/website/add/' + encodeURIComponent(val);
            const res = wUtils.sendRequest(url, {
                add_menu: $dialog.find('input[type="checkbox"]').is(':checked') || '',
            });
            return new Promise(function () {});
        });
    },
    /**
     * @private
     */
    _handleCloseDemand: function () {
        this._hideMenu();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set the focus on the first link
     *
     * @private
     */
    _focusFirstLink: function () {
        this.$firstLink.focus();
    },
    /**
     * Set the focus on the last link
     *
     * @private
     */
    _focusLastLink: function () {
        this.$lastLink.focus();
    },
    /**
     * Hide the menu
     *
     * @private
     */
    _hideMenu: function () {
        this.shown = false;
        this.$newContentMenuChoices.addClass('o_hidden');
        $('body').removeClass('o_new_content_open');
    },
    /**
     * Install a module
     *
     * @private
     * @param {number} moduleId: the module to install
     * @return {Promise}
     */
    _install: function (moduleId) {
        this.pendingInstall = true;
        $('body').css('pointer-events', 'none');
        return this._rpc({
            model: 'ir.module.module',
            method: 'button_immediate_install',
            args: [[moduleId]],
        }).guardedCatch(function () {
            $('body').css('pointer-events', '');
        });
    },
    /**
     * Show the menu
     *
     * @private
     * @returns {Promise}
     */
    _showMenu: function () {
        var self = this;
        return new Promise(function (resolve, reject) {
            self.trigger_up('action_demand', {
                actionName: 'close_all_widgets',
                onSuccess: resolve,
                onFailure: reject,
            });
        }).then(function () {
            self.firstTab = true;
            self.shown = true;
            self.$newContentMenuChoices.removeClass('o_hidden');
            $('body').addClass('o_new_content_open');
            self.$('> a').focus();
        });
    },
    /**
     * Called to add loader element in DOM.
     *
     * @param {string} moduleName
     * @private
     */
    _addLoader(moduleName) {
        const newContentLoaderText = _.str.sprintf(_t("Building your %s"), moduleName);
        this.$loader.find('#new_content_loader_text').replaceWith(newContentLoaderText);
        $('body').append(this.$loader);
    },
    /**
     * @private
     */
    _removeLoader() {
        this.$loader.remove();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the menu's toggle button is clicked:
     *  -> Opens the menu and reset the tab navigation (if closed)
     *  -> Close the menu (if open)
     * Called when a click outside the menu's options occurs -> Close the menu
     *
     * @private
     * @param {Event} ev
     */
    _onBackgroundClick: function (ev) {
        if (this.$newContentMenuChoices.hasClass('o_hidden')) {
            this._showMenu();
        } else {
            this._hideMenu();
        }
    },
    /**
     * Called when a keydown occurs:
     *  ESC -> Closes the modal
     *  TAB -> Navigation (captured in the modal)
     *
     * @private
     * @param {Event} ev
     */
    _onBackgroundKeydown: function (ev) {
        if (!this.shown) {
            return;
        }
        switch (ev.which) {
            case $.ui.keyCode.ESCAPE:
                this._hideMenu();
                ev.stopPropagation();
                break;
            case $.ui.keyCode.TAB:
                if (ev.shiftKey) {
                    if (this.firstTab || document.activeElement === this.$firstLink[0]) {
                        this._focusLastLink();
                        ev.preventDefault();
                    }
                } else {
                    if (this.firstTab || document.activeElement === this.$lastLink[0]) {
                        this._focusFirstLink();
                        ev.preventDefault();
                    }
                }
                this.firstTab = false;
                break;
        }
    },
    /**
     * Open the install dialog related to an element:
     *  - open the dialog depending on access right and another pending install
     *  - if ok to install, prepare the install action:
     *      - call the proper action on click
     *      - change the button text and style
     *      - handle the result (reload on the same page or error)
     *
     * @private
     * @param {Event} ev
     */
    _onModuleIdClick: function (ev) {
        var self = this;
        var $el = $(ev.currentTarget);
        var $i = $el.find('a i');
        var $p = $el.find('a p');

        var title = $p.text();
        var content = '';
        var buttons;

        var moduleId = $el.data('module-id');
        var name = $el.data('module-shortdesc');

        ev.stopPropagation();
        ev.preventDefault();

        if (this.pendingInstall) {
            content = this.newContentText.installInProgress;
        } else {
            content = _.str.sprintf(this.newContentText.installNeeded, name);
            buttons = [{
                text: _t("Install"),
                classes: 'btn-primary',
                close: true,
                click: function () {
                    // move the element where it will be after installation
                    var $finalPosition = self.$newContentMenuChoices
                        .find('.o_new_content_element:not([data-module-id])')
                        .filter(function () {
                            return $(this).data('original-index') < $el.data('original-index');
                        }).last();
                    if ($finalPosition) {
                        $el.fadeTo(400, 0, function () {
                            // if once installed, button disapeear, don't need to move it.
                            if (!$el.hasClass('o_new_content_element_once')) {
                                $el.insertAfter($finalPosition);
                            }
                            // change style to use spinner
                            $i.removeClass()
                                .addClass('fa fa-spin fa-circle-o-notch fa-spin')
                                .css('background-image', 'none');
                            $p.removeClass('o_uninstalled_module')
                                .text(_.str.sprintf(self.newContentText.installPleaseWait, name));
                            $el.fadeTo(1000, 1);
                            self._addLoader(name);
                        });
                    }

                    self._install(moduleId).then(function () {
                        var origin = window.location.origin;
                        var redirectURL = $el.find('a').data('url') || (window.location.pathname + '?' + enableFlag);
                        window.location.href = origin + redirectURL;
                        self._removeLoader();
                    }, function () {
                        $i.removeClass()
                            .addClass('fa fa-exclamation-triangle');
                        $p.text(_.str.sprintf(self.newContentText.failed, name));
                    });
                }
            }, {
                text: _t("Cancel"),
                close: true,
            }];
        }

        new Dialog(this, {
            title: title,
            size: 'medium',
            $content: $('<div/>', {text: content}),
            buttons: buttons
        }).open();
    },
});

registry.category("website_navbar_widgets").add("NewContentMenu", {
    Widget: NewContentMenu,
    selector: '.o_new_content_menu',
});

return NewContentMenu;
});
