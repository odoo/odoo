/*---------------------------------------------------------
 * OpenERP web_linkedin (module)
 *---------------------------------------------------------*/

openerp.web_linkedin = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    
    /*
    * instance.web_linkedin.tester.test_authentication()
    * Call check if the Linkedin session is open or open a connection popup
    * return a deferrer :
    *   - resolve if the authentication is true
    *   - reject if the authentication is wrong or when the user logout
    */
    instance.web_linkedin.LinkedinTester = instance.web.Class.extend({
        init: function() {
            this.linkedin_added = false;
            this.linkedin_def = $.Deferred();
            this.auth_def = $.Deferred();
        },
        error_catcher: function (callback) {
            var self = this;
            if (!this.realError) {
                this.realError = Error;
                this.window_onerror = window.onerror;
            }
            if (!callback) {
                Error = self.realError;
                return false;
            }
            this.callback = callback;
            window.onerror = function(message, fileName, lineNumber) {
                if (!window.onerror.prototype.catched) {
                    self.window_onerror(message, fileName, lineNumber);
                }
                if (self.realError != Error) {
                    window.onerror.prototype.catched = false;
                } else {
                    window.onerror = self.window_onerror;
                }
            };
            window.onerror.prototype.catched = false;
            Error = function (message, fileName, lineNumber) {
                this.name = message;
                this.message = message;
                this.fileName = fileName;
                this.lineNumber = lineNumber;
                this.caller = Error.caller.toString();
                window.onerror.prototype.catched = self.callback.apply(self, [this]);
                return this;
            };
            Error.prototype.toString = function () {return this.name;};
        },
        linkedin_disabled: function(error) {
            this.linkedin_def.reject();
            this.auth_def.reject();
            IN = false;
            var dialog = new instance.web.Dialog(this, {
                title: _t("LinkedIn is not enabled"),
                buttons: [
                    {text: _t("Ok"), click: function() { this.parents('.modal').modal('hide'); }}
                ],
            }, QWeb.render('LinkedIn.DisabledWarning', {error: error})).open();
        },
        test_linkedin: function() {
            var self = this;
            return this.test_api_key().then(function() {
                if (self.linkedin_added) {
                    return self.linkedin_def;
                }
                self.$linkedin = $('<div class="oe_linkedin_login_hidden" style="display:none;"><script type="in/Login"></script></div>');

                self.error_catcher(function (error) {
                    if (!!error.caller.match(/API Key is invalid/)) {
                        self.linkedin_disabled(error);
                        self.$linkedin.remove();
                        console.debug("LinkedIn JavaScript removed.");
                        self.linkedin_added = false;
                        self.error_catcher(false);
                        return true;
                    } else {
                        return false;
                    }
                });
                window.setTimeout(function () {self.error_catcher(false);}, 5000);

                $("body").append(self.$linkedin);
                var tag = document.createElement('script');
                tag.type = 'text/javascript';
                tag.src = "https://platform.linkedin.com/in.js";
                tag.innerHTML = 'api_key : ' + self.api_key + '\nauthorize : true\nscope: r_network r_basicprofile'; // r_contactinfo r_fullprofile r_emailaddress';
                
                document.getElementsByTagName('head')[0].appendChild(tag);
                self.linkedin_added = true;
                $(tag).load(function(event) {
                    console.debug("LinkedIn JavaScript inserted.");
                    IN.Event.on(IN, "frameworkLoaded", function() {
                        self.error_catcher(false);
                        console.debug("LinkedIn DOM node inserted and frameworkLoaded.");
                    });
                    IN.Event.on(IN, "systemReady", function() {
                        self.linkedin_def.resolve();
                        console.debug("LinkedIn systemReady.");
                    });
                    IN.Event.on(IN, "auth", function() {
                        self.auth_def.resolve();
                    });
                    IN.Event.on(IN, "logout", function() {
                        self.auth_def.reject();
                        self.auth_def = $.Deferred();
                    });
                });
                return self.linkedin_def.promise();
            });
        },
        test_api_key: function() {
            var self = this;
            if (this.api_key) {
                return $.when();
            }
            return new instance.web.Model("ir.config_parameter").call("get_param", ["web.linkedin.apikey"]).then(function(a) {
                if (!!a) {
                    self.api_key = a;
                    return true;
                } else {
                    return $.Deferred().reject();
                }
            });
        },
        test_authentication: function() {
            var self = this;
           this.linkedin_def.done(function () {
                if (IN.User.isAuthorized()) {
                    self.auth_def.resolve();
                } else {
                    IN.User.authorize();
                }
            });
            return this.auth_def.promise();
        },
    });
    
    instance.web_linkedin.tester = new instance.web_linkedin.LinkedinTester();
    
    instance.web_linkedin.Linkedin = instance.web.form.FieldChar.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.display_dm = new instance.web.DropMisordered(true);
        },
        initialize_content: function() {
            var $ht = $(QWeb.render("FieldChar.linkedin"));
            var $in = this.$("input");
            $in.replaceWith($ht);
            this.$(".oe_linkedin_input").append($in);
            this.$(".oe_linkedin_img").click(_.bind(this.search_linkedin, this));
            this._super();
        },
        search_linkedin: function() {
            var self = this;
            if (!this.open_in_process) {
                this.open_in_process = true;
                this.display_dm.add(instance.web_linkedin.tester.test_linkedin()).done(function() {
                    self.open_in_process = false;
                    var text = (self.get("value") || "").replace(/^\s+|\s+$/g, "").replace(/\s+/g, " ");
                    instance.web_linkedin.tester.test_authentication().done(function() {
                        var pop = new instance.web_linkedin.LinkedinSearchPopup(self, text);
                        pop.open();
                        pop.on("selected", this, function(entity) {
                            self.selected_entity(entity);
                        });
                    });
                });
            }
        },
        selected_entity: function(entity) {
            var self = this;
            this.create_on_change(entity).done(function(to_change) {
                var values = self.view.get_fields_values();
                _.each(to_change, function (value, key) {
                    if (!/linkedin/.test(key) && !!values[key]) {
                        if(!_.isArray(values[key])) {
                            delete to_change[key];
                        }
                    }
                })
                self.view.set_values(to_change);
            });
        },
        create_on_change: function(entity) {
            return entity.__type === "company" ? this.create_or_modify_company(entity) : this.create_or_modify_partner(entity);
        },
        create_or_modify_company: function (entity) {
            var self = this;
            var to_change = {};
            var image_def = null;
            to_change.is_company = true;
            to_change.name = entity.name;
            to_change.image = false;
            if (entity.logoUrl) {
                image_def = self.rpc('/web_linkedin/binary/url2binary',
                                   {'url': entity.logoUrl}).then(function(data){
                    to_change.image = data;
                });
            }
            to_change.website = entity.websiteUrl;
            to_change.phone = false;
            _.each((entity.locations || {}).values || [], function(el) {
                to_change.phone = el.contactInfo.phone1;
            });
            to_change.linkedin_url = _.str.sprintf("http://www.linkedin.com/company/%d", entity.id);

            _.each(to_change, function (val, key) {
                if (self.field_manager.datarecord[key]) {
                    to_change[key] = self.field_manager.datarecord[key];
                }
            });

            to_change.child_ids = [];
            var children_def = $.Deferred();
            IN.API.PeopleSearch().fields(commonPeopleFields).params({
                    "company-name" : entity.universalName,
                    "current-company": true,
                    "count": 50,
                }).result(function (result) {
                    console.debug("Linkedin pepople in this company found :", result.numResults, "=>", result.people._count, result.people.values);
                    var result = _.reject(result.people.values || [], function(el) {
                        return ! el.formattedName;
                    });
                    self.create_or_modify_company_partner(result).then(function (childs_to_change) {
                        _.each(childs_to_change, function (data) {
                            // [0,0,data] if it's a new partner
                            to_change.child_ids.push( data.id ? [1, data.id, data] : [0, 0, data] );
                        });
                        children_def.resolve();
                    });
                }).error(function () {
                    children_def.reject();
                });
            
            return $.when(image_def, children_def).then(function () {
                return to_change;
            });
        },
        create_or_modify_partner: function (entity, rpc_search_similar_partner) {
            var self = this;
            return this.create_or_modify_partner_change(entity).then(function (to_change) {
                // find similar partners
                _.each(to_change, function (val, key) {
                    if (self.field_manager.datarecord[key]) {
                        to_change[key] = self.field_manager.datarecord[key];
                    }
                });
            });
        },
        create_or_modify_partner_change: function (entity) {
            var to_change = {};
            var defs = [];
            to_change.is_company = false;
            to_change.name = entity.formattedName;
            if (entity.pictureUrl) {
                defs.push(this.rpc('/web_linkedin/binary/url2binary',
                                   {'url': entity.pictureUrl}).then(function(data){
                    to_change.image = data;
                }));
            }
            _.each((entity.phoneNumbers || {}).values || [], function(el) {
                if (el.phoneType === "mobile") {
                    to_change.mobile = el.phoneNumber;
                } else {
                    to_change.phone = el.phoneNumber;
                }
            });
            var positions = (entity.positions || {}).values || [];
            for (key in positions) {
                var position = positions[key];
                if (position.isCurrent) {
                    var company_name = position.company ? position.company.name : false;
                    if (!entity.parent_id && entity.parent_id !== 0 && company_name) {
                        defs.push(new instance.web.DataSetSearch(this, 'res.partner').call("search", [[["name", "=", company_name]]]).then(function (data) {
                            if(data[0]) to_change.parent_id = data[0];
                            else position.title = position.title + ' (' + company_name + ') ';
                            to_change.function = position.title;
                        }));
                    } else if (!entity.__company || !company_name || company_name == entity.__company) {
                        to_change.function = position.title + (company_name ? ' (' + company_name + ') ':'');
                    }
                    break;
                }
            };

            if (entity.parent_id) {
                to_change.parent_id = entity.parent_id;
            }
            to_change.linkedin_url = to_change.linkedin_public_url = entity.publicProfileUrl || false;
            to_change.linkedin_id = entity.id || false;

            return $.when.apply($, defs).then(function () {
                return to_change;
            });
        },
        create_or_modify_company_partner: function (entities) {
            var self = this;
            var deferrer = $.Deferred();
            var defs = [];
            var childs_to_change = [];

            _.each(entities, function (entity, key) {
                var entity = _.extend(entity, {
                    '__type': "people",
                    '__company': entity.universalName,
                    'parent_id': self.field_manager.datarecord.id || 0
                });
                defs.push(self.create_or_modify_partner_change(entity).then(function (to_change) {
                    childs_to_change[key] = to_change;
                }));
            });
            $.when.apply($, defs).then(function () {
                new instance.web.DataSetSearch(this, 'res.partner').call("linkedin_check_similar_partner", [entities]).then(function (partners) {
                    _.each(partners, function (partner, i) {
                        _.each(partner, function (val, key) {
                            if (val) {
                                childs_to_change[i][key] = val;
                            }
                        });
                    });
                    deferrer.resolve(childs_to_change);
                });
            });
            return deferrer;
        }
    });
    instance.web.form.widgets.add('linkedin', 'instance.web_linkedin.Linkedin');
    
    instance.web_linkedin.Linkedin_url = instance.web.form.FieldChar.extend({
        initialize_content: function() {
            this.$("input,span").replaceWith($(QWeb.render("FieldChar.linkedin_url")));
            this._super();
        },
        render_value: function() {
            this._super();
            this.$(".oe_linkedin_url").attr("href", this.field_manager.datarecord.linkedin_url || "#").toggle(!!this.field_manager.datarecord.linkedin_url);
        },
    });
    instance.web.form.widgets.add('linkedin_url', 'instance.web_linkedin.Linkedin_url');
    

    var commonPeopleFields = ["id", "picture-url", "public-profile-url", "first-name", "last-name",
                            "formatted-name", "location", "phone-numbers", "im-accounts",
                            "main-address", "headline", "positions", "summary", "specialties"];
    
    instance.web_linkedin.LinkedinSearchPopup = instance.web.Dialog.extend({
        template: "Linkedin.popup",
        init: function(parent, search) {
            var self = this;
            if (!IN.User.isAuthorized()) {
                this.$buttons = $("<div/>");
                this.destroy();
            }
            this._super(parent, { 'title': QWeb.render('LinkedIn.AdvancedSearch', {'title': _t("LinkedIn search")}) });
            this.search = search;
            this.limit = 5;
        },
        start: function() {
            this._super();
            this.bind_event();
            this.display_account();
            this.do_search();
        },
        bind_event: function() {
            var self = this;
            this.$el.parents('.modal').on("click", ".oe_linkedin_logout", function () {
                IN.User.logout();
                self.destroy();
            });
            this.$search = this.$el.parents('.modal').find(".oe_linkedin_advanced_search" );
            this.$url = this.$search.find("input[name='search']" );
            this.$button = this.$search.find("button");

            this.$button.on("click", function (e) {
                e.stopPropagation();
                self.do_search(self.$url.val() || '');
            });
            this.$url
                .on("click mousedown mouseup", function (e) {
                    e.stopPropagation();
                }).on("keydown", function (e) {
                    if(e.keyCode == 13) {
                        $(e.target).blur();
                        self.$button.click();
                    }
                });
        },
        display_account: function() {
            var self = this;
            IN.API.Profile("me")
                .fields(["firstName", "lastName"])
                .result(function (result) {
                    $(QWeb.render('LinkedIn.loginInformation', result.values[0])).appendTo(self.$el.parents('.modal').find(".oe_dialog_custom_buttons"));   
            })
        },
        do_search: function(url) {
            if (!IN.User || !IN.User.isAuthorized()) {
                this.destroy();
            }
            var self = this;
            var deferrers = [];
            this.$(".oe_linkedin_pop_c, .oe_linkedin_pop_p").empty();

            if (url && url.length) {
                var deferrer_c = $.Deferred();
                var deferrer_p = $.Deferred();
                deferrers.push(deferrer_c, deferrer_p);

                var url = url.replace(/\/+$/, '');
                var uid = url.replace(/(.*linkedin\.com\/[a-z]+\/)|(^.*\/company\/)|(\&.*$)/gi, '');

                IN.API.Raw(_.str.sprintf(
                        "companies/universal-name=%s:(id,name,logo-url,description,industry,website-url,locations,universal-name)",
                        encodeURIComponent(uid.toLowerCase()))).result(function (result) {
                    self.do_result_companies({'companies': {'values': [result]}});
                    deferrer_c.resolve();
                }).error(function (error) {
                    self.do_result_companies({});
                    deferrer_c.resolve();
                });

                var url_public = "http://www.linkedin.com/pub/"+uid;
                IN.API.Profile("url="+ encodeURI(url_public).replace(/%2F/g, '/'))
                    .fields(commonPeopleFields)
                    .result(function(result) {
                        self.do_result_people({'people': result});
                        deferrer_p.resolve();
                }).error(function (error) {
                    self.do_warn( _t("LinkedIn error"), _t("LinkedIn is temporary down for the searches by url."));
                    self.do_result_people({});
                    deferrer_p.resolve();
                });

                this.search = url;
            }

            var deferrer_c_k = $.Deferred();
            var deferrer_p_k = $.Deferred();
            deferrers.push(deferrer_c_k, deferrer_p_k);
            IN.API.Raw(_.str.sprintf(
                    "company-search:(companies:" +
                    "(id,name,logo-url,description,industry,website-url,locations,universal-name))?keywords=%s&count=%d",
                    encodeURI(this.search), this.limit)).result(function (result) {
                self.do_result_companies(result);
                deferrer_c_k.resolve();
            });
            IN.API.PeopleSearch().fields(commonPeopleFields).params({"keywords": this.search, "count": this.limit}).result(function(result) {
                self.do_result_people(result);
                deferrer_p_k.resolve();
            });

            return $.when.apply($, deferrers);
        },
        do_result_companies: function(companies) {
            var lst = (companies.companies || {}).values || [];
            lst = _.first(lst, this.limit);
            lst = _.map(lst, function(el) {
                el.__type = "company";
                return el;
            });
            console.debug("Linkedin companies found:", (companies.companies || {})._total, '=>', lst.length, lst);
            return this.display_result(lst, this.$(".oe_linkedin_pop_c"));
        },
        do_result_people: function(people) {
            var plst = (people.people || {}).values || [];
            plst = _.first(plst, this.limit);
            plst = _.map(plst, function(el) {
                el.__type = "people";
                return el;
            });
            console.debug("Linkedin people found:", people.numResults, '=>', plst.length, plst);
            return this.display_result(plst, this.$(".oe_linkedin_pop_p"));
        },
        display_result: function(result, $elem) {
            var self = this;
            var $row;
            $elem.find(".oe_no_result").remove();
            _.each(result, function(el) {
                var pc = new instance.web_linkedin.EntityWidget(self, el);
                if (!$elem.find("div").size() || $elem.find(" > div:last > div").size() >= 5) {
                    $row = $("<div style='display: table-row;width:100%'/>");
                    $row.appendTo($elem);
                }
                pc.appendTo($row);
                pc.$el.css("display", "table-cell");
                pc.$el.css("width", "20%");
                pc.on("selected", self, function(data) {
                    self.trigger("selected", data);
                    self.destroy();
                });
            });
            if (!$elem.find("div").size()) {
                $elem.append($('<div class="oe_no_result">').text(_t("No results found")));
            }
        },
        
    });
    
    instance.web_linkedin.EntityWidget = instance.web.Widget.extend({
        template: "Linkedin.EntityWidget",
        init: function(parent, data) {
            this._super(parent);
            this.data = data;
        },
        start: function() {
            var self = this;
            this.$el.click(function() {
                self.trigger("selected", self.data);
            });
            if (this.data.__type === "company") {
                this.$("h3").text(this.data.name);
                self.$("img").attr("src", this.data.logoUrl);
                self.$(".oe_linkedin_entity_headline").text(this.data.industry);
            } else { // people
                this.$("h3").text(this.data.formattedName);
                self.$("img").attr("src", this.data.pictureUrl);
                self.$(".oe_linkedin_entity_headline").text(this.data.headline);
            }
        },
    });
};
// vim:et fdc=0 fdl=0:
