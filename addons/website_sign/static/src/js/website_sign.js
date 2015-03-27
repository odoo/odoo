
odoo.define('website_sign.page', function(require) {
    'use strict';

    var core = require('web.core');
    var ajax = require('web.ajax');
    var Widget = require('web.Widget');
    var Class = require('web.Class');
    var website = require('website.website');
    
    var CLASSES = {};
    var WIDGETS = {};

    var websiteSign = null;

    /* -------------------------------------------------- */
    /*  WebsiteSign Class (set of some useful functions)  */
    /* -------------------------------------------------- */
    CLASSES.WebsiteSign = Class.extend({
        init: function() {
            this.currentRole = $('.parties_input_info').first().data('id');
            this.types = {};
        },

        getPartnerSelectConfiguration: function() {
            var self = this;

            if(self.getPartnerSelectConfiguration.def === undefined) {
                self.getPartnerSelectConfiguration.def = new $.Deferred();

                var select2Options = {
                    allowClear: true,

                    formatResult: function(data, resultElem, searchObj) {
                        var partner = $.parseJSON(data.text);
                        if($.isEmptyObject(partner)) {
                            var partnerInfo = self.partnerRegexMatch(searchObj.term);
                            var $elem = $(data.element[0]);
                            if(!partnerInfo) {
                                $elem.removeData('name mail');
                                return "Create: \"" + searchObj.term + "\" <span class='fa fa-exclamation-circle' style='color:rgb(255, 192, 128);'/> <span style='font-size:0.7em'>Enter mail (and name if you want)</span>";
                            }
                            else {
                                $elem.data(partnerInfo);
                                return "Create: \"" + $elem.data('name') + " (" + $elem.data('mail') + ")" + "\" <span class='fa fa-check-circle' style='color:rgb(128, 255, 128);'/>";
                            }
                        }

                        var $item = $("<div>" + ((partner['new'])? "New: " : "") + partner['name'] + " (" + partner['email'] + ")" + "</div>");
                        $item.css('border-bottom', '1px dashed silver');
                        return $item;
                    },

                    formatSelection: function(data) {
                        var partner = $.parseJSON(data.text);
                        if($.isEmptyObject(partner))
                            return "Error";

                        return ((partner['new'])? "New: " : "") + partner['name'] + " (" + partner['email'] + ")";
                    },

                    matcher: function(search, data) {
                        var partner = $.parseJSON(data);
                        if($.isEmptyObject(partner))
                            return (search.length > 0);

                        var searches = search.toUpperCase().split(/[ ()]/);
                        for(var i = 0 ; i < searches.length ; i++) {
                            if(partner['email'].toUpperCase().indexOf(searches[i]) < 0 && partner['name'].toUpperCase().indexOf(searches[i]) < 0)
                                return false;
                        }
                        return true;
                    }
                };

                var selectChangeHandler = function(e) {
                    if(e.added && e.added.element.length > 0) {
                        var $option = $(e.added.element[0]);
                        var $select = $option.parent();
                        if(parseInt($option.val()) !== 0)
                            return true;

                        setTimeout(function() {
                            $select.select2("destroy");

                            if(!$option.data('mail'))
                                $option.prop('selected', false);
                            else {
                                if(!$select.data('newNumber'))
                                    $select.data('newNumber', 0);
                                var newNumber = $select.data('newNumber') - 1;
                                $select.data('newNumber', newNumber);

                                $option.val(newNumber);
                                $option.html('{"name": "' + $option.data('name') + '", "email": "' + $option.data('mail') + '", "new": "1"}');

                                var $newOption = $('<option value="0">{}</option>');
                                $select.find('option').filter(':last').after($newOption);
                            }

                            $select.select2(select2Options);
                        }, 0);

                        return false;
                    }
                    else if(e.removed && e.removed.element.length > 0) {
                        var $option = $(e.removed.element[0]);
                        var $select = $option.parent();
                        if(parseInt($option.val()) >= 0)
                            return true;

                        setTimeout(function() {
                            $select.select2("destroy");
                            $select.find('option[value=' + $option.val() + ']').remove();
                            $select.select2(select2Options);
                        }, 0);
                    }
                };

                return ajax.jsonRpc("/sign/get_partners", 'call', {}).then(function(data) {
                    var $partnerSelect = $('<select><option/></select>');
                    for(var i = 0 ; i < data.length ; i++) {
                        var $option = $('<option value="' + data[i]['id'] + '">' + JSON.stringify(data[i]) + '</option>');
                        $partnerSelect.append($option);
                    }
                    $partnerSelect.append($('<option value="0">{}</option>'));

                    return self.getPartnerSelectConfiguration.def.resolve($partnerSelect.html(), select2Options, selectChangeHandler);
                });
            }

            return self.getPartnerSelectConfiguration.def;
        },

        setAsPartnerSelect: function($select) {
            return this.getPartnerSelectConfiguration().then(function(selectHTML, select2Options, selectChangeHandler) {
                $select.select2('destroy');
                $select.html(selectHTML).css('width', '100%').addClass('form-control');
                $select.select2(select2Options);
                $select.off('change').on('change', selectChangeHandler);
            });
        },

        partnerRegexMatch: function(str) {
            var partnerInfo = str.match(/(?:\s|\()*(((?:\w|-|\.)+)@(?:\w|-)+\.(?:\w|-)+)(?:\s|\))*/);
            if(!partnerInfo || partnerInfo[1] === undefined)
                return false;
            else {
                var name = "";
                var index = str.indexOf(partnerInfo[0]);
                name = str.substr(0, index) + " " + str.substr(index+partnerInfo[0].length);
                if(name === " ")
                    name = partnerInfo[2];

                return {'name': name, 'mail': partnerInfo[1]};
            }
        },

        processPartnersSelectionThen: function($select, thenFunction) {
            var partnerIDs = $select.val();
            if(!partnerIDs || partnerIDs.length <= 0)
                return false;

            if(typeof partnerIDs === 'string')
                partnerIDs = [parseInt(partnerIDs)];

            var partners = [];
            var waitForPartnerCreations = [];
            $(partnerIDs).each(function(i, partnerID){
                partnerID = parseInt(partnerID);
                if(partnerID < 0) {
                    var partnerInfo = $.parseJSON($select.find('option[value=' + partnerID + ']').html());
                    waitForPartnerCreations.push(ajax.jsonRpc("/sign/new_partner", 'call', {
                        'name': partnerInfo.name.trim(),
                        'mail': partnerInfo.email.trim()
                    }).then(function(pID) {
                        partners.push(pID);
                    }));
                }
                else if(partnerID === 0)
                    return;
                else
                    partners.push(partnerID);
            });

            return $.when.apply($, waitForPartnerCreations).then(function() {
                thenFunction(partners);
            });
        },

        getResponsibleSelectConfiguration: function() {
            var self = this;

            if(self.getResponsibleSelectConfiguration.def === undefined) {
                self.getResponsibleSelectConfiguration.def = new $.Deferred();

                var select2Options = {
                    placeholder: "Select the responsible",
                    allowClear: false,

                    formatResult: function(data, resultElem, searchObj) {
                        if(!data.text) {
                            $(data.element[0]).data('create_name', searchObj.term);
                            return "Create: \"" + searchObj.term + "\"";
                        }
                        return data.text;
                    },

                    formatSelection: function(data) {
                        if(!data.text)
                            return $(data.element[0]).data('create_name');
                        return data.text;
                    },

                    matcher: function(search, data) {
                        if(!data)
                            return (search.length > 0);
                        return (data.toUpperCase().indexOf(search.toUpperCase()) > -1);
                    }
                };

                var selectChangeHandler = function(e) {
                    var $select = $(e.target), $option = $(e.added.element[0]);

                    var resp = parseInt($option.val());
                    var name = $option.html() || $option.data('create_name');
                    
                    if(resp >= 0 || !name)
                        return false;

                    ajax.jsonRpc("/sign/add_signature_item_party", 'call', {
                        'name': name
                    }).then(function(partyID) {
                        var $newResponsibleOption = $('<input type="hidden"/>');
                        $newResponsibleOption.data({id: partyID, name: name}).addClass('parties_input_info');
                        $('.parties_input_info').filter(':last').after($newResponsibleOption);

                        self.getResponsibleSelectConfiguration.def = undefined;
                        self.setAsResponsibleSelect($select, partyID);
                    });
                };

                var $responsibleSelect = $('<select><option/></select>');
                $('.parties_input_info').each(function(i, el) {
                    $responsibleSelect.append($('<option value="' + parseInt($(el).data('id')) + '">' + $(el).data('name') + '</option>'));
                });
                $responsibleSelect.append($('<option value="-1"/>'));

                return self.getResponsibleSelectConfiguration.def.resolve($responsibleSelect.html(), select2Options, selectChangeHandler);
            }

            return self.getResponsibleSelectConfiguration.def;
        },

        setAsResponsibleSelect: function($select, selected) {
            return this.getResponsibleSelectConfiguration().then(function(selectHTML, select2Options, selectChangeHandler) {
                $select.select2('destroy');
                $select.html(selectHTML).css('width', '100%').addClass('form-control');
                if(selected !== undefined)
                    $select.val(selected);
                $select.select2(select2Options);
                $select.off('change').on('change', selectChangeHandler);
            });
        },

        getResponsibleName: function(responsibleID) {
            return $('.parties_input_info').filter(function(i, el) {
                return (parseInt($(el).data('id')) === responsibleID);
            }).first().data('name');
        },

        getTypeData: function(id) {
            var self = this;

            if($.isEmptyObject(self.types)) {
                $("input[type='hidden'].field_type_input_info").each(function(i, el) {
                    var $elem = $(el);
                    self.types[$elem.data('item-type-id')] = {
                        'id': $elem.data('item-type-id'),
                        'name': $elem.data('item-type-name'),
                        'type': $elem.data('item-type-type'),
                        'tip': $elem.data('item-type-tip'),
                        'placeholder': $elem.data('item-type-placeholder'),
                        'default_width': $elem.data('item-type-width'),
                        'default_height': $elem.data('item-type-height'),
                        'auto_field': $elem.data('item-type-auto')
                    };
                });
            }
            return self.types[id];
        },
    });

    /* ------------------------- */
    /*  Signature Dialog Widget  */
    /* ------------------------- */
    WIDGETS.SignatureDialog = Widget.extend({
        template: 'website_sign.signature_dialog',

        events: {
            'shown.bs.modal': function(e) {
                var width = this.$signatureField.width();
                var height = width / this.signatureRatio;

                this.$signatureField.empty().jSignature({
                    'decor-color': 'transparent',
                    'background-color': '#FFF',
                    'color': '#000',
                    'lineWidth': 2,
                    'width': width,
                    'height': height
                });
                this.emptySignature = this.$signatureField.jSignature("getData");

                this.addOdooSigned(this.$signatureField, true);

                this.$modeButtons.filter('.btn-primary').click();
                this.$('.modal-footer .btn-primary').prop('disabled', false).focus();
            },

            'click a.sign_mode': function(e) {
                this.$modeButtons.removeClass('btn-primary');
                $(e.target).addClass('btn-primary');
                this.$signatureField.jSignature('reset');

                this.mode = $(e.target).prop('id');

                this.$selectStyleButton.toggle(this.mode === 'auto_sign_mode');
                this.$clearButton.toggle(this.mode === 'draw_sign_mode');
                this.$loadButton.toggle(this.mode === 'load_sign_mode');

                if(this.mode === 'load_sign_mode')
                    this.$loadButton.click();
                this.$signatureField.jSignature((this.mode === 'draw_sign_mode')? "enable" : "disable");

                this.$fontDialog.hide().css('width', 0);
                this.$signerNameInput.trigger('input');
            },

            'input #signer_name': function(e) {
                if(this.mode !== "auto_sign_mode")
                    return true;
                this.printText(this.getSignatureFont(this.currentFont), this.getSignatureText());
            },

            'click #sign_select_style': function(e) {
                var self = this;

                self.$fontDialog.find('a').html('<div class="loading"/>');
                self.$fontDialog.show().animate({'width': self.$fontDialog.find('a').first().height() * self.signatureRatio * 1.25}, 500, function() {
                    self.buildPreviewButtons();
                });
            },

            'mouseover #font_dialog a': function(e) {
                this.currentFont = $(e.currentTarget).data('font-nb');
                this.$signerNameInput.trigger('input');
            },

            'click #font_dialog a, #sign': function(e) {
                this.$fontDialog.hide().css('width', 0);
            },

            'click #sign_clean': function (e) {
                this.$signatureField.jSignature('reset');
            },

            'change #sign_load': function(e) {
                var self = this;

                var f = e.target.files[0];
                if(f.type.substr(0, 5) !== "image")
                    return false;

                var reader = new FileReader();
                reader.onload = function(e) {
                    self.printImage(this.result);
                };
                reader.readAsDataURL(f);
            },

            'click .modal-footer .btn-primary': function(e) {
                this.confirmFunction(this.$signerNameInput.val(), this.$signatureField.jSignature("getData"));
            },
        },

        init: function(parent, signerName) {
            this._super(parent);

            this.signerName = signerName;

            this.signatureRatio = 3.0;
            this.signatureType = 'signature';

            this.emptySignature = null;
            this.fonts = null;

            this.currentFont = 0;
            this.mode = "auto_sign_mode";

            this.confirmFunction = function() {};
        },

        start: function() {
            var self = this;

            self.$modeButtons = self.$('a.sign_mode');
            self.$signatureField = self.$("#sign");
            self.$fontDialog = self.$("#font_dialog");
            self.$fontSelection = self.$("#sign_font_selection");
            self.$clearButton = self.$('#sign_clean');
            self.$selectStyleButton = self.$('#sign_select_style');
            self.$loadButton = self.$('#sign_load');
            self.$signerNameInput = self.$("#signer_name");

            return $.when(this._super(), self.getSignatureFont().then(function(data) {
                for(var i = 0 ; i < data.length ; i++) {
                    var name = data[i][0];
                    if(name.length > 15)
                        name = name.substr(0, 12) + "...";
                    var $button = $("<a data-font-nb='" + i + "'>" + name + "</a>");
                    $button.addClass('btn btn-block')

                    self.$fontSelection.append($button);
                }
            }));
        },

        addOdooSigned: function($item, powered) {
            $item.addClass('odoo_signed');
            if(powered) {
                var token = window.location.href.match(/\/([\w-]{25,})/)[1];
                $item.prepend($('<div class="small text-center odoo_signed_powered">' + token + '</div>'));
            }
        },

        getSignatureText: function() {
            var text = this.$signerNameInput.val();
            if(this.signatureType === 'initial') {
                var words = text.split(' ');
                text = "";
                for(var i = 0 ; i < words.length ; i++) {
                    if(words[i].length > 0)
                        text += words[i][0] + '.';
                }
            }
            return text;
        },

        getSVGText: function(font, text) {
            return ("data:image/svg+xml;base64," + btoa(core.qweb.render('website_sign.svg_text', {
                width: this.$signatureField.find('canvas')[0].width,
                height: this.$signatureField.find('canvas')[0].height,
                font: font,
                text: text,
                type: this.signatureType
            })));
        },

        printText: function(font, text) {
            return this.printImage(this.getSVGText(font, text));
        },

        printImage: function(imgSrc) {
            var self = this;

            if(self.printImage.def === undefined)
                self.printImage.def = (new $.Deferred()).resolve();

            self.printImage.def = self.printImage.def.then(function() {
                var newDef = new $.Deferred();

                var image = new Image;
                image.onload = function() {
                    var width = 0, height = 0;
                    var ratio = image.width/image.height

                    self.$signatureField.jSignature('reset');
                    var $canvas = self.$signatureField.find('canvas'), context = $canvas[0].getContext("2d");

                    if(image.width / $canvas[0].width > image.height / $canvas[0].height) {
                        width = $canvas[0].width;
                        height = width / ratio;
                    }
                    else {
                        height = $canvas[0].height;
                        width = height * ratio;
                    }

                    setTimeout(function() {
                        $(context.drawImage(image, 0, 0, image.width, image.height, ($canvas[0].width - width)/2, ($canvas[0].height - height)/2, width, height)).promise().then(function() {
                            newDef.resolve();
                        });
                    }, 0);
                };
                image.src = imgSrc;

                return newDef;
            });

            return self.printImage.def;
        },

        buildPreviewButtons: function() {
            var self = this;

            self.$fontDialog.find('a').each(function(i, el) {
                var $img = $('<img src="' + self.getSVGText(self.getSignatureFont($(el).data('font-nb')), self.getSignatureText()) + '"/>');
                self.addOdooSigned($img, false);
                $(el).empty().append($img);
            });
        },

        getSignatureFont: function(no) {
            var self = this;

            if(!self.fonts)
                return ajax.jsonRpc('/sign/get_fonts', 'call', {}).then(function(data) {
                    self.fonts = data;
                    return data;
                });
            return (no >= 0 && no < self.fonts.length)? self.fonts[no][1] : false;
        },

        onConfirm: function(fct) {
            this.confirmFunction = fct;
        },
    });

    /* --------------------------- */
    /*  Item Customization Dialog  */
    /* --------------------------- */
    WIDGETS.ItemCustomizationDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                var resp = parseInt(this.$responsibleSelect.find('select').val());
                var required = this.$('input[type="checkbox"]').prop('checked');

                websiteSign.currentRole = resp;
                this.$currentTarget.data({responsible: resp, required: required});

                this.$currentTarget.trigger('itemChange');
            },

            'click #delete_field_button': function(e) {
                this.$currentTarget.trigger('itemDelete');
            }
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$responsibleSelect = this.$('#responsible_select');
            return this._super();
        },

        setTarget: function($signatureItem) {
            this.$currentTarget = $signatureItem;
            websiteSign.setAsResponsibleSelect(this.$responsibleSelect.find('select'), $signatureItem.data('responsible'));
            this.$('input[type="checkbox"]').prop('checked', $signatureItem.data('required'));

            this.$('.modal-header .modal-title span').html('<span class="fa fa-long-arrow-right"/> ' + $signatureItem.prop('title') + ' Field');
        }
    });

    /* ------------------------------ */
    /*  Ask Multiple Initials Dialog  */
    /* ------------------------------ */
    WIDGETS.AskMultipleInitialsDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                this.updateTargetResponsible();
                this.$currentTarget.trigger('itemChange');
            },

            'click .modal-footer .btn-default': function(e) {
                this.updateTargetResponsible();
                this.$currentTarget.trigger('itemClone');
            }
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$responsibleSelect = this.$('#responsible_select_initials');
            return this._super();
        },

        setTarget: function($signatureItem) {
            this.$currentTarget = $signatureItem;
            websiteSign.setAsResponsibleSelect(this.$responsibleSelect.find('select'), websiteSign.currentRole);
        },

        updateTargetResponsible: function() {
            var resp = parseInt(this.$responsibleSelect.find('select').val());
            if(resp)
                websiteSign.currentRole = resp;
            this.$currentTarget.data('responsible', resp);
        },
    });

    /* --------------------------------- */
    /*  Signature Item Navigator Widget  */
    /* --------------------------------- */
    WIDGETS.SignatureItemNavigator = Widget.extend({
        className: 'signature_item_navigator',

        events: {
            'click': 'onClick'
        },

        init: function(parent) {
            this._super(parent);

            this.iframeWidget = parent;
            this.started = false;
        },

        start: function() {
            this.$signatureItemNavLine = $('<div class="signature_item_navline"/>');
            this.$signatureItemNavLine.insertBefore(this.$el);

            this.setTip('start');
            this.$el.focus();

            return this._super();
        },

        setTip: function(tip) {
            this.$el.html('<span class="helper"/>' + tip);
        },

        onClick: function(e) {
            var self = this;

            if(!self.started) {
                self.started = true;

                self.iframeWidget.$iframe.prev().animate({'height': '0px', 'opacity': 0}, {
                    duration: 750,
                    progress: function() {
                        self.iframeWidget.resize(false);
                    },
                    complete: function() {
                        self.iframeWidget.$iframe.prev().hide();
                        self.iframeWidget.resize(true);

                        self.onClick();
                    }
                });
                
                return false;
            }

            var $toComplete = self.iframeWidget.checkSignatureItemsCompletion().sort(function(a, b) {
                return ($(a).data('order') || 0) - ($(b).data('order') || 0);
            });
            if($toComplete.length > 0)
                self.scrollToSignItem($toComplete.first());
        },

        scrollToSignItem: function($item) {
            var self = this;

            if(!self.started)
                return;

            var containerHeight = self.iframeWidget.$('#viewerContainer').outerHeight();
            var viewerHeight = self.iframeWidget.$('#viewer').outerHeight();

            var scrollOffset = containerHeight/4;
            var scrollTop = $item.offset().top - self.iframeWidget.$('#viewer').offset().top - scrollOffset;
            if(scrollTop + containerHeight > viewerHeight)
                scrollOffset += scrollTop + containerHeight - viewerHeight;
            if(scrollTop < 0)
                scrollOffset += scrollTop;
            scrollOffset += self.iframeWidget.$('#viewerContainer').offset().top - self.$el.outerHeight()/2 + parseInt($item.css('height'))/2;

            var duration = Math.min(1000, 
                5*(Math.abs(self.iframeWidget.$('#viewerContainer')[0].scrollTop - scrollTop) + Math.abs(parseFloat(self.$el.css('top')) - scrollOffset)));

            self.iframeWidget.$('#viewerContainer').animate({'scrollTop': scrollTop}, duration);
            self.$el.add(self.$signatureItemNavLine).animate({'top': scrollOffset}, duration, 'swing', function() {
                if($item.val() === "" && !$item.data('signature'))
                    self.$el.html('<span class="helper"/>' + websiteSign.getTypeData($item.data('type'))['tip']);
            });

            self.iframeWidget.$('.ui-selected').removeClass('ui-selected');
            $item.addClass('ui-selected').focus();
        },
    });

    /* ------------------- */
    /*  PDF Iframe Widget  */
    /* ------------------- */
    WIDGETS.PDFIframe = Widget.extend({
        events: {
            'keydown .page .ui-selected': function(e) {
                if((e.keyCode || e.which) !== 9)
                    return true;

                e.preventDefault(); 
                this.signatureItemNav.onClick();
            },

            'click #toolbarContainer': 'delayedRefresh',

            'itemChange .signature_item': function(e) {
                this.updateSignatureItem($(e.target));
                this.$iframe.trigger('templateChange');
            },

            'itemDelete .signature_item': function(e) {
                this.deleteSignatureItem($(e.target));
                this.$iframe.trigger('templateChange');
            },

            'itemClone .signature_item': function(e) {
                var $target = $(e.target);
                this.updateSignatureItem($target);
                for(var i = 1 ; i <= this.nbPages ; i++) {
                    var ignore = false;
                    for(var j = 0 ; j < this.configuration[i].length ; j++) {
                        if(websiteSign.getTypeData(this.configuration[i][j].data('type'))['type'] === 'signature')
                            ignore = true;
                    }
                    if(ignore)
                        continue;

                    var $newElem = $target.clone(true);
                    this.enableCustom($newElem);
                    this.configuration[i].push($newElem);
                }
                this.deleteSignatureItem($target);
                this.refreshSignatureItems();
                this.$iframe.trigger('templateChange');
            }
        },

        init: function(parent, $iframe, editMode) {
            this._super(parent);

            this.$iframe = $iframe;

            this.nbPages = 0;

            this.editMode = editMode;
            this.readonlyFields = (this.$iframe.attr('readonly') === "readonly") || editMode;
            this.pdfView = window.location.href.indexOf('pdfview') > -1 || (this.$iframe.attr('readonly') === "readonly");

            this.role = parseInt($('#input_current_role').val()) || 0;

            this.$fieldTypeToolbar = null;
            this.currentFieldType = false;
            this.configuration = {};

            this.types = {};

            this.refreshTimer = null;

            this.fullyLoaded = new $.Deferred();
        },

        start: function(attachmentLocation, $signatureItemsInfo) {
            var self = this;

            var resizeWindowTimer = null;
            $(window).on('resize', function(e) {
                clearTimeout(resizeWindowTimer);
                resizeWindowTimer = setTimeout(function() {self.resize(true);}, 200);
            });

            var viewerURL = ((!self.editMode)? "../" : "") + "../../website_sign/static/lib/pdfjs/web/viewer.html?file=";
            viewerURL += encodeURIComponent(attachmentLocation).replace(/'/g,"%27").replace(/"/g,"%22") + "#page=1&zoom=page-width";
            self.$iframe.attr('src', viewerURL);
            
            $('body').css('overflow', 'hidden');

            self.waitForPDF($signatureItemsInfo);
            return $.when(self._super(), self.fullyLoaded.promise());
        },

        waitForPDF: function($signatureItemsInfo) {
            var self = this;

            if(self.$iframe.contents().find('#errorMessage').is(":visible"))
                return alert('Need a valid PDF to add signature fields !');

            var nbPages = self.$iframe.contents().find('.page').length;
            var nbLayers = self.$iframe.contents().find('.textLayer').length;
            if(nbPages > 0 && nbLayers > 0) {
                self.nbPages = nbPages;
                self.doPDFPostLoad($signatureItemsInfo);
            }
            else
                setTimeout(function() { self.waitForPDF($signatureItemsInfo); }, 50);
        },

        resize: function(refresh) {
            this.$iframe.css('height', $('body').outerHeight()-this.$iframe.offset().top);
            if(refresh)
                this.refreshSignatureItems();
        },

        doPDFPostLoad: function($signatureItemsInfo) {
            var self = this;

            self.setElement(self.$iframe.contents().find('html'));
            self.resize(false);

            self.$('#openFile, #pageRotateCw, #pageRotateCcw, #pageRotateCcw').hide();
            self.$('button#print').prop('title', "Print original document");
            self.$('button#download').prop('title', "Download original document");
            self.$('button#zoomOut').click();
            
            for(var i = 1 ; i <= self.nbPages ; i++)
                self.configuration[i] = [];

            var $cssLink = $("<link rel='stylesheet' type='text/css' href='../../../../../website_sign/static/src/css/iframe.css'/>");
            var $faLink = $("<link rel='stylesheet' href='../../../../../web/static/lib/fontawesome/css/font-awesome.css'/>");
            var $jqueryLink = $("<link rel='stylesheet' href='/web/static/lib/jquery.ui/jquery-ui.css'/><script type='text/javascript' src='/web/static/lib/jquery.ui/jquery-ui.js'></script>");
            self.$('head').append($cssLink, $faLink, $jqueryLink);

            var waitFor = [];

            if(self.editMode) {
                if(self.$iframe.attr('disabled') === 'disabled') {
                    self.$('#viewer').fadeTo('slow', 0.75);
                    var $div = $('<div style="position:absolute; top:0; left:0; width:100%; height:100%; z-index:110; opacity:0.75;"/>');
                    self.$('#viewer').css('position', 'relative').prepend($div);
                    $div.on('click mousedown mouseup mouveover mouseout', function(e) {
                        return false;
                    });
                }
                else {
                    var $fieldTypeButtons = $('.field_type_button');
                    self.$fieldTypeToolbar = $('<div/>').addClass('field_type_toolbar');
                    self.$fieldTypeToolbar.prependTo(self.$('#viewerContainer'));
                    $fieldTypeButtons.detach().appendTo(self.$fieldTypeToolbar).draggable({
                        cancel: false,
                        helper: function(e) {
                            self.currentFieldType = $(this).data('item-type-id');
                            
                            var type = websiteSign.getTypeData(self.currentFieldType);
                            var $signatureItem = self.createSignatureItem(self.currentFieldType, true, websiteSign.currentRole, 0, 0, type["default_width"], type["default_height"]);

                            if(!e.ctrlKey)
                                self.$('.signature_item').removeClass('ui-selected');
                            $signatureItem.prop('id', 'signature_item_to_add').addClass('ui-selected');

                            self.$('.page').first().append($signatureItem);
                            self.updateSignatureItem($signatureItem);
                            $signatureItem.css('width', $signatureItem.css('width')).css('height', $signatureItem.css('height')); // Convert % to px
                            $signatureItem.detach();
                            
                            return $signatureItem;
                        }
                    });

                    self.$('.page').droppable({
                        accept: '*',
                        tolerance: 'touch',
                        drop: function(e, ui) {
                            if(ui.helper.prop('id') !== 'signature_item_to_add')
                                return true;

                            var $parent = $(e.target);
                            var pageNo = parseInt($parent.prop('id').substr('pageContainer'.length));

                            ui.helper.removeAttr('id');
                            var $signatureItem = ui.helper.clone(true).removeClass().addClass('signature_item signature_item_required');

                            var posX = (ui.offset.left - $parent.find('.textLayer').offset().left) / $parent.innerWidth();
                            var posY = (ui.offset.top - $parent.find('.textLayer').offset().top) / $parent.innerHeight();
                            $signatureItem.data({posx: posX, posy: posY});

                            self.configuration[pageNo].push($signatureItem);
                            self.refreshSignatureItems();
                            self.updateSignatureItem($signatureItem);
                            self.enableCustom($signatureItem);

                            self.$iframe.trigger('templateChange');

                            if(websiteSign.getTypeData($signatureItem.data('type'))['type'] === 'initial') {
                                self.askMultipleInitialsDialog.setTarget($signatureItem);
                                self.askMultipleInitialsDialog.$el.modal('show');
                            }

                            self.currentFieldType = false;

                            return false;
                        }
                    });

                    self.$('#viewer').selectable({
                        appendTo: self.$('body'), 
                        filter: '.signature_item'
                    });

                    var keyFct = function(e) {
                        if(e.which !== 46)
                            return true;

                        self.$('.ui-selected').each(function(i, el) {
                            self.deleteSignatureItem($(el));
                        });
                        self.$iframe.trigger('templateChange');
                    };
                    $(document).on('keyup', keyFct);
                    self.$el.on('keyup', keyFct);
                }

                self.itemCustomDialog = new WIDGETS.ItemCustomizationDialog(self, $('#signature_item_custom_dialog'));
                waitFor.push(self.itemCustomDialog.start());

                self.askMultipleInitialsDialog = new WIDGETS.AskMultipleInitialsDialog(self, $('#initial_all_page_dialog'));
                waitFor.push(self.askMultipleInitialsDialog.start());
            }
            else {
                self.signatureItemNav = new WIDGETS.SignatureItemNavigator(self);
                waitFor.push(self.signatureItemNav.prependTo(self.$('#viewerContainer')));
            }

            $signatureItemsInfo.sort(function(a, b) {
                var $a = $(a), $b = $(b);

                if($a.data('page') !== $b.data('page'))
                    return ($a.data('page') - $b.data('page'));

                if(Math.abs($a.data('posy') - $b.data('posy')) > 0.01)
                    return ($a.data('posy') - $b.data('posy'));
                else
                    return ($a.data('posx') - $b.data('posx'));
            }).each(function(i, el){
                var $elem = $(el);
                var $signatureItem = self.createSignatureItem(
                    $elem.data('type'), $elem.data('required') === "True", parseInt($elem.data('responsible')) || 0,
                    parseFloat($elem.data('posx')), parseFloat($elem.data('posy')), $elem.data('width'), $elem.data('height'),
                    $elem.data('item-value'));
                $signatureItem.data('item-id', $elem.data('item-id'));
                $signatureItem.data('order', i);

                self.configuration[parseInt($elem.data('page'))].push($signatureItem);
            }); 

            $.when.apply($, waitFor).then(function() {
                self.refreshSignatureItems();

                self.$('.signature_item').each(function(i, el) {
                    if(self.editMode)
                        self.enableCustom($(el));
                    self.updateSignatureItem($(el));
                });

                if(!self.editMode)
                    self.checkSignatureItemsCompletion();

                self.$('#viewerContainer').on('scroll', function(e) {
                    if(!self.editMode && self.signatureItemNav.started)
                        self.signatureItemNav.setTip('next');
                    self.delayedRefresh();
                });

                self.$('#viewerContainer').css('visibility', 'visible').animate({'opacity': 1}, 1000);

                self.fullyLoaded.resolve();
            });
        },

        delayedRefresh: function(e) {
            var self = this;

            clearTimeout(self.refreshTimer);

            self.refreshTimer = setTimeout(function() {
                self.refreshSignatureItems();
            }, 500);
        },

        refreshSignatureItems: function() {
            var $focusItem = this.$('.signature_item:focus').first();

            for(var page in this.configuration) {
                var $pageContainer = this.$('body #pageContainer' + page);
                for(var i = 0 ; i < this.configuration[page].length ; i++)
                    $pageContainer.append(this.configuration[page][i].detach());
            }
            this.updateFontSize();

            if($focusItem.length > 0 && !this.editMode)
                this.signatureItemNav.scrollToSignItem($focusItem);
        },

        updateFontSize: function() {
            var self = this;

            var normalSize = self.$('.page').first().innerHeight() * 0.015;

            self.$('.signature_item').each(function(i, el) {
                var $elem = $(el);
                var size = parseFloat($elem.css('height'));
                if($.inArray(websiteSign.getTypeData($elem.data('type'))['type'], ['signature', 'initial', 'textarea']) > -1)
                    size = normalSize;

                $elem.css('font-size', size * 0.8);
            }); 
        },

        createSignatureItem: function(typeID, required, responsible, posX, posY, width, height, value) {
            var self = this;

            var readonly = self.readonlyFields || (responsible > 0 && responsible !== self.role);
            var type = websiteSign.getTypeData(typeID);

            var $signatureItem = $(core.qweb.render('website_sign.signature_item', {
                readonly: readonly,
                type: type['type'],
                value: (value)? ("" + value).split('\n').join('<br/>') : "",
                placeholder: type['placeholder']
            }));

            if(!readonly) {
                if(type['type'] === "signature" || type['type'] === "initial") {
                    $signatureItem.on('click', function(e) {
                        var $signedItems = self.$('.signature_item').filter(function(i) {
                            var $item = $(this);
                            return ($item.data('type') === type['id']
                                        && $item.data('signature') && $item.data('signature') !== $signatureItem.data('signature')
                                        && ($item.data('responsible') <= 0 || $item.data('responsible') === $signatureItem.data('responsible')));
                        });
                        
                        if($signedItems.length > 0) {
                            $signatureItem.data('signature', $signedItems.first().data('signature'));
                            $signatureItem.html('<span class="helper"/><img src="' + $signatureItem.data('signature') + '"/>');
                            $signatureItem.trigger('input');
                        }
                        else {
                            websiteSign.signatureDialog.signatureType = type['type'];
                            websiteSign.signatureDialog.signatureRatio = parseFloat($signatureItem.css('width'))/parseFloat($signatureItem.css('height'));
                            websiteSign.signatureDialog.$el.modal('show');

                            websiteSign.signatureDialog.onConfirm(function(name, signature) {
                                if(signature !== websiteSign.signatureDialog.emptySignature) {
                                    $signatureItem.data('signature', signature);
                                    $signatureItem.html('<span class="helper"/><img src="' + $signatureItem.data('signature') + '"/>');
                                }
                                else {
                                    $signatureItem.removeData('signature');
                                    $signatureItem.html("<span class='helper'/>" + type['placeholder']);
                                }

                                $signatureItem.trigger('input').focus();
                                websiteSign.signatureDialog.$el.modal('hide');
                            });
                        }
                    });
                }

                if(type['auto_field']) {
                    $signatureItem.on('focus', function(e) {
                        if($signatureItem.val() === "") {
                            $signatureItem.val(type['auto_field']);
                            $signatureItem.trigger('input');
                        }
                    });
                }

                $signatureItem.on('input', function(e) {
                    self.checkSignatureItemsCompletion(self.role);
                    self.signatureItemNav.setTip('next');
                });
            }

            $signatureItem.data({type: type['id'], required: required, responsible: responsible, posx: posX, posy: posY, width: width, height: height});
            return $signatureItem;
        },

        deleteSignatureItem: function($item) {
            var pageNo = parseInt($item.parent().prop('id').substr('pageContainer'.length));
            $item.remove();
            for(var i in this.configuration[pageNo]) {
                if(this.configuration[pageNo][i].data('posx') === $item.data('posx') && this.configuration[pageNo][i].data('posy') === $item.data('posy'))
                    this.configuration[pageNo].splice(i, 1);
            }
        },

        enableCustom: function($signatureItem) {
            var self = this;

            $signatureItem.prop('title', websiteSign.getTypeData($signatureItem.data('type'))['name']);

            var configArea = $signatureItem.find('.config_area');
            configArea.show();

            configArea.find('.fa.fa-arrows').on('mouseup', function(e) {
                if(!e.ctrlKey) {
                    self.$('.signature_item').filter(function(i) {
                        return (this !== $signatureItem[0]);
                    }).removeClass('ui-selected');
                }
                $signatureItem.toggleClass('ui-selected');
            });

            $signatureItem.add(configArea.find('.responsible_display')).on('mousedown', function(e) {
                if(e.target !== e.currentTarget)
                    return true;

                self.$('.ui-selected').removeClass('ui-selected');
                $signatureItem.addClass('ui-selected');

                self.itemCustomDialog.setTarget($signatureItem);
                self.itemCustomDialog.$el.modal("show");
            });

            $signatureItem.draggable({containment: "parent", handle: ".fa-arrows"}).resizable({containment: "parent"}).css('position', 'absolute');

            $signatureItem.on('dragstart resizestart', function(e, ui) {
                if(!e.ctrlKey)
                    self.$('.signature_item').removeClass('ui-selected');
                $signatureItem.addClass('ui-selected');
            });

            $signatureItem.on('dragstop', function(e, ui) {
                $signatureItem.data('posx', Math.round((ui.position.left / $signatureItem.parent().innerWidth())*1000)/1000);
                $signatureItem.data('posy', Math.round((ui.position.top / $signatureItem.parent().innerHeight())*1000)/1000);

                self.updateSignatureItem($signatureItem);
                self.$iframe.trigger('templateChange');
                $signatureItem.removeClass('ui-selected');
            });

            $signatureItem.on('resizestop', function(e, ui) {
                $signatureItem.data('width', Math.round(ui.size.width/$signatureItem.parent().innerWidth()*1000)/1000);
                $signatureItem.data('height', Math.round(ui.size.height/$signatureItem.parent().innerHeight()*1000)/1000);

                self.updateSignatureItem($signatureItem);
                self.$iframe.trigger('templateChange');
                $signatureItem.removeClass('ui-selected');
            });
        },

        updateSignatureItem: function($signatureItem) {
            var posX = $signatureItem.data('posx'), posY = $signatureItem.data('posy');
            var width = $signatureItem.data('width'), height = $signatureItem.data('height');

            if(posX < 0)
                posX = 0;
            else if(posX+width > 1.0)
                posX = 1.0-width;
            if(posY < 0)
                posY = 0;
            else if(posY+height > 1.0)
                posY = 1.0-height;

            $signatureItem.data({posx: Math.round(posX*1000)/1000, posy: Math.round(posY*1000)/1000});

            $signatureItem.css({'left': posX*100 + '%', 'top': posY*100 + '%'});
            $signatureItem.css({'width': width*100 + '%', 'height': height*100 + '%'});

            if(this.editMode) {
                var responsibleName = websiteSign.getResponsibleName($signatureItem.data('responsible'));
                $signatureItem.find('.responsible_display').html(responsibleName).prop('title', responsibleName);
            }

            var resp = $signatureItem.data('responsible');
            $signatureItem.toggleClass('signature_item_required', ($signatureItem.data('required') && (this.editMode || resp <= 0 || resp === this.role)));
            $signatureItem.toggleClass('signature_item_pdfview', (this.pdfView || (resp !== this.role && resp > 0 && !this.editMode)));
        },

        checkSignatureItemsCompletion: function() {
            var $toComplete = this.$('.signature_item.signature_item_required:not(.signature_item_pdfview)').filter(function(i, el) {
                return !($(el).val() || $(el).data('signature'));
            });

            this.signatureItemNav.$el.add(this.signatureItemNav.$signatureItemNavLine).toggle($toComplete.length > 0);
            this.$iframe.trigger(($toComplete.length > 0)? 'pdfToComplete' : 'pdfCompleted');

            return $toComplete;
        },
    });

    /* --------------------------------- */
    /*  Create Signature Request Dialog  */
    /* --------------------------------- */
    WIDGETS.CreateSignatureRequestDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                this.sendDocument();
            },
        },

        init: function(parent, $root, templateID) {
            this._super(parent);
            this.setElement($root);

            this.templateID = templateID;
        },

        start: function() {
            this.$subjectInput = this.$('#signature_request_subject_input');
            this.$messageInput = this.$('#sign_message_textarea');
            this.$referenceInput = this.$('#sign_reference_input');

            return this._super();
        },

        launch: function(rolesToChoose, templateName) {
            this.$subjectInput.val('Signature Request - ' + templateName);
            var defaultRef = templateName + this.$referenceInput.data('endref');
            this.$referenceInput.val(defaultRef).attr('placeholder', defaultRef);

            this.$('#warning_message_no_field').toggle($.isEmptyObject(rolesToChoose));
            this.$('#request_signers .new_signer').remove();

            // Followers
            websiteSign.setAsPartnerSelect(self.$('#request_signers .form-group select'));
            
            // Signers
            if($.isEmptyObject(rolesToChoose))
                this.addSigner(0, "Signers", true);
            else {
                var roleIDs = Object.keys(rolesToChoose).sort();
                for(var i = 0 ; i < roleIDs.length ; i++) {
                    var roleID = roleIDs[i];
                    if(roleID !== 0)
                        this.addSigner(roleID, rolesToChoose[roleID], false);
                }
            }

            this.$el.modal('show');
        },

        addSigner: function(roleID, roleName, multiple) {
            var $newSigner = $('<div/>');
            $newSigner.addClass('new_signer form-group');

            var $signerRoleLabel = $('<label/>');
            $signerRoleLabel.addClass('col-md-3 control-label').html(roleName).data('role', roleID);
            $newSigner.append($signerRoleLabel);
            
            var $signerInfo = $('<select placeholder="Write email or search contact..."/>');
            if(multiple)
                $signerInfo.attr('multiple', 'multiple');

            var $signerInfoDiv = $('<div/>');
            $signerInfoDiv.addClass('col-md-9');
            $signerInfoDiv.append($signerInfo);

            $newSigner.append($signerInfoDiv);

            websiteSign.setAsPartnerSelect($signerInfo);

            this.$('#request_signers').prepend($newSigner);
        },

        sendDocument: function() {
            var self = this;

            var completedOk = true;
            self.$('.new_signer').each(function(i, el) {
                var $elem = $(el);
                var partnerIDs = $elem.find('select').val();
                if(!partnerIDs || partnerIDs.length <= 0) {
                    completedOk = false;
                    $elem.addClass('has-error');
                    $elem.one('focusin', function(e) {
                        $elem.removeClass('has-error');
                    });
                }
            });
            if(!completedOk)
                return false;

            var waitFor = [];

            var signers = [];
            self.$('.new_signer').each(function(i, el) {
                var $elem = $(el);
                var selectDef = websiteSign.processPartnersSelectionThen($elem.find('select'), function(partners) {
                    for(var p = 0 ; p < partners.length ; p++) {
                        signers.push({
                            'partner_id': partners[p],
                            'role': parseInt($elem.find('label').data('role'))
                        });
                    }
                });
                if(selectDef !== false)
                    waitFor.push(selectDef);
            });

            var followers = [];
            var followerDef = websiteSign.processPartnersSelectionThen(self.$('#followers_select'), function(partners) {
                followers = partners;
            });
            if(followerDef !== false)
                waitFor.push(followerDef);

            var subject = self.$subjectInput.val() || self.$subjectInput.attr('placeholder');
            var reference = self.$referenceInput.val() || self.$referenceInput.attr('placeholder');
            var message = self.$messageInput.val();
            $.when.apply($, waitFor).then(function(result) {
                ajax.jsonRpc("/sign/create_document/" + self.templateID, 'call', {
                    'signers': signers,
                    'reference': reference,
                    'followers': followers,
                    'subject': subject,
                    'message': message,
                    'send': true
                }).then(function(requestID) {
                    window.location.href = "/sign/document/" + requestID + "?pdfview&message=3";
                });
            });
        },
    });

    /* ----------------------- */
    /*  Share Template Dialog  */
    /* ----------------------- */
    WIDGETS.ShareTemplateDialog = Widget.extend({
        events: {
            'focus #share_link_input': function(e) {
                $(e.target).select();
            },
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$linkInput = this.$('#share_link_input');
            return this._super();
        },

        launch: function(templateID) {
            var self = this;

            var $formGroup = self.$linkInput.closest('.form-group');
            $formGroup.hide();
            $formGroup.next().hide();
            var linkStart = window.location.href.substr(0, window.location.href.indexOf('/sign')) + '/sign/';

            ajax.jsonRpc("/sign/share/" + templateID, 'call', {}).then(function(link) {
                self.$linkInput.val((link)? (linkStart + link) : '');
                $formGroup.toggle(link);
                $formGroup.next().toggle(!link);

                self.$el.modal('show');
            });
        },
    });

    /* ---------------------- */
    /*  Add Followers Dialog  */
    /* ---------------------- */
    WIDGETS.AddFollowersDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                websiteSign.processPartnersSelectionThen(this.$select, function(partners) {
                    ajax.jsonRpc($(e.target).data('ref'), 'call', {
                        'followers': partners
                    }).then(function(requestID) {
                        window.location.href = "/sign/document/" + requestID + "?pdfview";
                    });
                });
            },
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$select = this.$('#followers_select');
            return this._super();
        },

        launch: function() {
            websiteSign.setAsPartnerSelect(this.$select);
            this.$el.modal('show');
        },
    });

    /* ---------------------- */
    /*  Public Signer Dialog  */
    /* ---------------------- */
    WIDGETS.PublicSignerDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                var self = this;

                var name = self.$el.find('input').eq(0).val();
                var mail = self.$el.find('input').eq(1).val();
                if(!name || !mail)
                    return false;

                ajax.jsonRpc($(e.target).data('ref'), 'call', {
                    'name': name,
                    'mail': mail
                }).then(function() {
                    self.$el.modal('hide');
                    return self.thenFunction();
                });
            }
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);

            this.thenFunction = function() {};
        },

        launch: function(name, mail, thenFunction) {
            if(this.$el.length <= 0)
                return thenFunction();

            this.$el.find('input').eq(0).val(name);
            this.$el.find('input').eq(1).val(mail);

            this.thenFunction = thenFunction;
            this.$el.modal('show');
        },
    });

    /* ------------------------- */
    /*  WebsiteSign Page Widget  */
    /* ------------------------- */
    WIDGETS.WebsiteSignPage = Widget.extend({
        events: {
            'click .fa-pencil': function(e) {
                this.$templateNameInput.focus().select();
            },

            'input #template_name_input': function(e) {
                this.$templateNameInput.attr('size', this.$templateNameInput.val().length);
            },

            'change #template_name_input': function(e) {
                this.saveTemplate();
                if(this.$templateNameInput.val() === "")
                    this.$templateNameInput.val(this.initialTemplateName);
            },

            'click #send_template_button': function(e) {
                this.saveTemplate();
                this.createSignatureRequestDialog.launch(this.rolesToChoose, this.$templateNameInput.val());
            },

            'click #share_template_button': function(e) {
                this.shareTemplateDialog.launch(this.templateID);
            },

            'click #cancel_request_button': function(e) {
                ajax.jsonRpc($(e.target).data('ref'), 'call', {}).then(function(data) {
                    window.location.href = "/sign";
                });
            },

            'click .resend_access_button': function(e) {
                ajax.jsonRpc("/sign/resend_access", 'call', {
                    'id': parseInt($(e.target).data('id'))
                }).then(function(data) {
                    $(e.target).removeClass('fa fa-envelope').html("Resent !");
                });
            },

            'click #add_followers_button': function(e) {
                this.addFollowersDialog.launch();
            },

            'templateChange iframe.website_sign_iframe': function(e) {
                this.saveTemplate();
            },

            'click #duplicate_signature_template': function(e) {
                this.saveTemplate(true);
            },

            'pdfToComplete iframe.website_sign_iframe': function(e) {
                this.$validateBanner.hide().css('opacity', 0);
            },

            'pdfCompleted iframe.website_sign_iframe': function(e) {
                this.$validateBanner.show().animate({'opacity': 1}, 500);
            },

            'click #signature-validate-banner button': 'signItemDocument',
            'click #sign-document-button': 'signDocument',
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);

            this.iframeWidget = null;
            this.rolesToChoose = {};
        },

        start: function() {
            var self = this;

            var defStarts = [self._super()];

            self.attachmentLocation = self.$('#input_attachment_location').val();
            self.templateID = parseInt(self.$('#input_signature_request_template_id').val());
            self.requestID = parseInt(self.$('#input_signature_request_id').val());

            self.$templateNameInput = self.$('#template_name_input');
            self.$templateNameInput.trigger('input');
            self.initialTemplateName = self.$templateNameInput.val();

            self.$iframe = self.$('iframe.website_sign_iframe');
            
            self.$buttonSendTemplate = self.$('#send_template_button');
            self.$validateBanner = self.$('#signature-validate-banner');

            var editMode = !self.requestID;
            if(editMode) {
                self.createSignatureRequestDialog = new WIDGETS.CreateSignatureRequestDialog(self, self.$('#create_signature_request_dialog'), self.templateID);
                defStarts.push(self.createSignatureRequestDialog.start());
                self.shareTemplateDialog = new WIDGETS.ShareTemplateDialog(self, self.$('#share_template_dialog'));
                defStarts.push(self.shareTemplateDialog.start());
            }
            else {
                self.addFollowersDialog = new WIDGETS.AddFollowersDialog(self, self.$('#add_followers_dialog'));
                defStarts.push(self.addFollowersDialog.start());
                self.publicSignerDialog = new WIDGETS.PublicSignerDialog(self, self.$('#public_signer_dialog'));
                defStarts.push(self.publicSignerDialog.start());
            }

            if(self.$iframe.length > 0) {
                self.$buttonSendTemplate.prop('disabled', true);

                self.iframeWidget = new WIDGETS.PDFIframe(self, self.$iframe, editMode);
                defStarts.push(self.iframeWidget.start(self.attachmentLocation, self.$iframe.parent().find("input[type='hidden'].item_input_info")).then(function(e) {
                    self.$buttonSendTemplate.prop('disabled', false);
                }));       
            }

            return $.when.apply($, defStarts);
        },

        saveTemplate: function(duplicate) {
            duplicate = (duplicate === undefined)? false : duplicate;

            this.rolesToChoose = {};
            var data = {};
            var newId = 0;
            var configuration = (this.iframeWidget)? this.iframeWidget.configuration : {};
            for(var page in configuration) {
                for(var i = 0 ; i < configuration[page].length ; i++) {
                    var resp = configuration[page][i].data('responsible');

                    data[configuration[page][i].data('item-id') || (newId--)] = {
                        'type_id': configuration[page][i].data('type'),
                        'required': configuration[page][i].data('required'),
                        'responsible_id': resp,
                        'page': page,
                        'posX': configuration[page][i].data('posx'),
                        'posY': configuration[page][i].data('posy'),
                        'width': configuration[page][i].data('width'),
                        'height': configuration[page][i].data('height'),
                    };

                    this.rolesToChoose[resp] = websiteSign.getResponsibleName(resp);
                }
            }

            var $majInfo = self.$('#template-saved-info');

            ajax.jsonRpc("/sign/update_template/" + this.templateID + ((duplicate)? '/duplicate' : '/update'), 'call', {
                'signature_items': data,
                'name': this.$templateNameInput.val() || this.initialTemplateName
            }).then(function (templateID) {
                if(!duplicate) {
                    $majInfo.stop();
                    $majInfo.css('opacity', 1);
                    $majInfo.animate({'opacity': 0}, 1500);
                }
                else
                    window.location.href = '/sign/template/' + templateID;
            });
        },

        signItemDocument: function(e) {
            var self = this;

            var mail = "";
            self.iframeWidget.$('.signature_item').each(function(i, el){
                if($(el).val().indexOf('@') >= 0)
                    mail = $(el).val();
            });

            self.publicSignerDialog.launch(websiteSign.signatureDialog.$signerNameInput.val(), mail, function() {
                var ok = true;

                var signatureValues = {};
                self.iframeWidget.$('.signature_item:not(.signature_item_pdfview)').each(function(i, el){
                    var $elem = $(el);
                    var value = $elem.val();
                    if($elem.data('signature'))
                        value = (($elem.data('signature') !== websiteSign.signatureDialog.emptySignature)? $elem.data('signature') : false);

                    var resp = parseInt($elem.data('responsible')) || 0;

                    if(!value) {
                        if($elem.data('required') && (resp <= 0 || resp === self.role))
                            ok = false;
                        return;
                    }

                    signatureValues[parseInt($elem.data('item-id'))] = value;
                });

                if(!ok)
                    return alert("Some fields must be completed !");

                self.$el.fadeTo('slow', 0.75);
                var $div = $('<div/>');
                $div.addClass('sign_loading_div');
                $div.html("<span class='helper'/><span>Sign in progress...<br/>(this may take a while, you can leave the page if you want)</span>");
                self.$el.append($div);

                ajax.jsonRpc($(e.target).data('action'), 'call', {
                    'sign': signatureValues
                }).then(function (data) {
                    window.location.href = '/sign/document/'+data['id']+'/'+data['token']+'?message=2&pdfview';
                });
            });
        },

        signDocument: function(e) {
            var self = this;

            websiteSign.signatureDialog.onConfirm(function(name, signature) {
                var isEmpty = ((signature)? (websiteSign.signatureDialog.emptySignature === signature) : true);

                websiteSign.signatureDialog.$('#signer_info').toggleClass('has-error', !name);
                websiteSign.signatureDialog.$('#signature_draw').toggleClass('panel-danger', isEmpty).toggleClass('panel-default', !isEmpty);
                if(isEmpty || !name)
                    return false;

                websiteSign.signatureDialog.$('.modal-footer .btn-primary').prop('disabled', true);
                websiteSign.signatureDialog.$el.modal('hide');

                self.publicSignerDialog.launch(name, "", function() {
                    ajax.jsonRpc($(e.target).data("action"), 'call', {
                        'sign': (signature)? signature.substr(signature.indexOf(",")+1) : false,
                    }).then(function (data) {
                        window.location.href = '/sign/document/'+data['id']+'/'+data['token']+'?message=2';
                    });
                });
            });
        },
    });

    /* ----------------- */
    /*  Initializations  */
    /* ----------------- */
    website.add_template_file('/website_sign/static/src/xml/website_sign.xml');
    website.if_dom_contains('#is_website_sign_page', function() {
        website.ready().then(function() {
            websiteSign = new CLASSES.WebsiteSign();

            var websiteSignPage = new WIDGETS.WebsiteSignPage(null, $('body'));
            websiteSign.signatureDialog = new WIDGETS.SignatureDialog(null, $('#signer_name_input_info').val());

            /* ------------- */
            /*  Geolocation  */
            /* ------------- */
            if($('#ask_location_input').val() && navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    ajax.jsonRpc($('#ask_location_input').val(), 'call', {
                        'latitude': position.coords.latitude,
                        'longitude': position.coords.longitude
                    });
                });
            }

            return websiteSignPage.start().then(function() {
                return websiteSign.signatureDialog.appendTo(websiteSignPage.$el);
            });
        });
    });
    
    return {
        'classes': CLASSES,
        'widgets': WIDGETS
    };
});
