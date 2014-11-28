(function () {
    'use strict';

    var website = openerp.website;

    CKEDITOR.plugins.add('customColor', {
        requires: 'panelbutton,floatpanel',
        init: function (editor) {
            function create_button (buttonID, label) {
                var btnID = buttonID;
                editor.ui.add(buttonID, CKEDITOR.UI_PANELBUTTON, {
                    label: label,
                    title: label,
                    modes: { wysiwyg: true },
                    editorFocus: true,
                    context: 'font',
                    panel: {
                        css: [  '/web/css/web.assets_common/' + (new Date().getTime()),
                                '/web/css/website.assets_frontend/' + (new Date().getTime()),
                                '/web/css/website.assets_editor/' + (new Date().getTime())],
                        attributes: { 'role': 'listbox', 'aria-label': label },
                    },
                    enable: function () {
                        this.setState(CKEDITOR.TRISTATE_OFF);
                    },
                    disable: function () {
                        this.setState(CKEDITOR.TRISTATE_DISABLED);
                    },
                    onBlock: function (panel, block) {
                        var self = this;
                        var html = openerp.qweb.render('website_less.colorpicker');
                        block.autoSize = true;
                        block.element.setHtml( html );
                        $(block.element.$).on('click', 'button', function () {
                            self.clicked(this);
                        });
                        if (btnID === "TextColor") {
                            $(".only-text", block.element.$).css("display", "block");
                            $(".only-bg", block.element.$).css("display", "none");
                        }
                        var $body = $(block.element.$).parents("body");
                        setTimeout(function () {
                            $body.css('background-color', '#fff');
                        }, 0);
                    },
                    getClasses: function () {
                        var self = this;
                        var classes = [];
                        var id = this._.id;
                        var block = this._.panel._.panel._.blocks[id];
                        var $root = $(block.element.$);
                        $root.find("button").map(function () {
                            var color = self.getClass(this);
                            if(color) classes.push( color );
                        });
                        return classes;
                    },
                    getClass: function (button) {
                        var color = btnID === "BGColor" ? $(button).attr("class") : $(button).attr("class").replace(/^bg-/i, 'text-');
                        return color.length && color;
                    },
                    clicked: function (button) {
                        var className = this.getClass(button);
                        var ancestor = editor.getSelection().getCommonAncestor();

                        editor.focus();
                        this._.panel.hide();
                        editor.fire('saveSnapshot');

                        // remove style
                        var classes = [];
                        var $ancestor = $(ancestor.$);
                        var $fonts = $(ancestor.$).find('font');
                        if (!ancestor.$.tagName) {
                            $ancestor = $ancestor.parent();
                        }
                        if ($ancestor.is('font')) {
                            $fonts = $fonts.add($ancestor[0]);
                        }

                        $fonts.filter("."+this.getClasses().join(",.")).map(function () {
                            var className = $(this).attr("class");
                            if (classes.indexOf(className) === -1) {
                                classes.push(className);
                            }
                        });
                        for (var k in classes) {
                            editor.removeStyle( new CKEDITOR.style({
                                element: 'font',
                                attributes: { 'class': classes[k] },
                            }) );
                        }

                        // add new style
                        if (className) {
                            editor.applyStyle( new CKEDITOR.style({
                                element: 'font',
                                attributes: { 'class': className },
                            }) );
                        }
                        editor.fire('saveSnapshot');
                    }

                });
            }
            create_button("BGColor", "Background Color");
            create_button("TextColor", "Text Color");
        }
    });

    website.RTE = website.RTE.extend({
        _config: function () {
            var config = this._super.apply(this, arguments);
            config.extraPlugins = 'customColor,' + config.extraPlugins;
            return config
        },
    });
})();
