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
            instance.web.dialog($(QWeb.render("LinkedIn.DisabledWarning", {'error': error})), {
                title: _t("LinkedIn is not enabled"),
                buttons: [
                    {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
                ]
            });
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
            this.display_dm.add(instance.web_linkedin.tester.test_linkedin()).done(function() {
                var pop = new instance.web_linkedin.LinkedinPopup(self, self.get("value"));
                pop.open();
                pop.on("selected", this, function(entity) {
                    self.selected_entity(entity);
                });
            });
        },
        selected_entity: function(entity) {
            var self = this;
            this.create_on_change(entity).done(function(to_change) {
                self.view.set_values(to_change);
            });
        },
        create_on_change: function(entity) {
            var self = this;
            var to_change = {};
            var defs = [];
            if (entity.__type === "company") {
                to_change.is_company = true;
                to_change.name = entity.name;
                to_change.image = false;
                if (entity.logoUrl) {
                    defs.push(self.rpc('/web_linkedin/binary/url2binary',
                                       {'url': entity.logoUrl}).then(function(data){
                        to_change.image = data;
                    }));
                }
                to_change.website = entity.websiteUrl;
                to_change.phone = false;
                _.each((entity.locations || {}).values || [], function(el) {
                    to_change.phone = el.contactInfo.phone1;
                });
                var children_def = $.Deferred();
                IN.API.PeopleSearch().fields(commonPeopleFields).params({
                        "company-name" : entity.name,
                        "current-company": true,
                        "count": 25,
                    }).result(function(result) {
                        children_def.resolve(result);
                    }).error(function() {
                        children_def.reject();
                    });
                defs.push(children_def.then(function(result) {
                    result = _.reject(result.people.values || [], function(el) {
                        return ! el.formattedName;
                    });
                    var defs = _.map(result, function(el) {
                        el.__type = "people";
                        return self.create_on_change(el);
                    });
                    return $.when.apply($, defs).then(function() {
                        var p_to_change = _.toArray(arguments);
                        to_change.child_ids = p_to_change;
                    });
                }, function() {
                    return $.when();
                }));
                /* TODO
                to_change.linkedinUrl = _.str.sprintf("http://www.linkedin.com/company/%d", entity.id);
                */
            } else { // people
                to_change.is_company = false;
                to_change.name = entity.formattedName;
                to_change.image = false;
                if (entity.pictureUrl) {
                    defs.push(self.rpc('/web_linkedin/binary/url2binary',
                                       {'url': entity.pictureUrl}).then(function(data){
                        to_change.image = data;
                    }));
                }
                to_change.mobile = false;
                to_change.phone = false;
                _.each((entity.phoneNumbers || {}).values || [], function(el) {
                    if (el.phoneType === "mobile") {
                        to_change.mobile = el.phoneNumber;
                    } else {
                        to_change.phone = el.phoneNumber;
                    }
                });
                var positions = (entity.positions || {}).values || [];
                to_change.function = positions.length > 0 ? positions[0].title : false;
                /* TODO
                to_change.linkedinUrl = entity.publicProfileUrl;
                */
            }
            return $.when.apply($, defs).then(function() {
                return to_change;
            });
        },
    });
    
    instance.web.form.widgets.add('linkedin', 'instance.web_linkedin.Linkedin');
    
    var commonPeopleFields = ["id", "picture-url", "public-profile-url",
                            "formatted-name", "location", "phone-numbers", "im-accounts",
                            "main-address", "headline", "positions"];
    
    instance.web_linkedin.LinkedinPopup = instance.web.Dialog.extend({
        template: "Linkedin.popup",
        init: function(parent, text) {
            this._super(parent, {title:_t("LinkedIn search")});
            this.text = text;
            this.limit = 5;
        },
        start: function() {
            this._super();
            var self = this;
            this.on("authentified", this, this.authentified);
            instance.web_linkedin.tester.test_authentication().done(function() {
                self.trigger("authentified");
            });
        },
        authentified: function() {
            var self = this;
            cdef = $.Deferred();
            pdef = $.Deferred();
            IN.API.Raw(_.str.sprintf(
                    "company-search:(companies:" +
                    "(id,name,logo-url,description,industry,website-url,locations))?keywords=%s&count=%d",
                    encodeURI(this.text), this.limit)).result(function (result) {
                cdef.resolve(result);
            });
            var def = cdef.then(function(companies) {
                var lst = companies.companies.values || [];
                lst = _.first(lst, self.limit);
                lst = _.map(lst, function(el) {
                    el.__type = "company";
                    return el;
                });
                console.debug("Linkedin companies found:", lst.length, lst);
                return self.display_result(lst, self.$(".oe_linkedin_pop_c"));
            });
            IN.API.PeopleSearch().fields(commonPeopleFields).
                params({"keywords": this.text, "count": this.limit}).result(function(result) {
                pdef.resolve(result);
            });
            var def2 = pdef.then(function(people) {
                var plst = people.people.values || [];
                plst = _.first(plst, self.limit);
                plst = _.map(plst, function(el) {
                    el.__type = "people";
                    return el;
                });
                console.debug("Linkedin people found:", plst.length, plst);
                return self.display_result(plst, self.$(".oe_linkedin_pop_p"));
            });
            return $.when(def, def2);
        },
        display_result: function(result, $elem) {
            var self = this;
            var i = 0;
            var $row;
            _.each(result, function(el) {
                var pc = new instance.web_linkedin.EntityWidget(self, el);
                if (i % 5 === 0) {
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
                i++;
            });
            if (result.length === 0) {
                $elem.text(_t("No results found"));
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
            } else { // people
                this.$("h3").text(this.data.formattedName);
                self.$("img").attr("src", this.data.pictureUrl);
                self.$(".oe_linkedin_entity_headline").text(this.data.headline);
            }
        },
    });
};
// vim:et fdc=0 fdl=0:
