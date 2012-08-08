/*---------------------------------------------------------
 * OpenERP web_linkedin (module)
 *---------------------------------------------------------*/

openerp.web_linkedin = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    
    instance.web_linkedin.LinkedinTester = instance.web.Class.extend({
        init: function() {
            this.linkedin_added = false;
            this.linkedin_def = $.Deferred();
            this.auth_def = $.Deferred();
        },
        test_linkedin: function() {
            var self = this;
            return this.test_api_key().pipe(function() {
                if (self.linkedin_added)
                    return self.linkedin_def.promise();
                var tag = document.createElement('script');
                tag.type = 'text/javascript';
                tag.src = "http://platform.linkedin.com/in.js";
                tag.innerHTML = 'api_key : ' + self.api_key + '\nauthorize : true';
                document.getElementsByTagName('head')[0].appendChild(tag);
                self.linkedin_added = true;
                $(tag).load(function() {
                    IN.Event.on(IN, "auth", function() {
                        self.auth_def.resolve();
                    });
                    self.linkedin_def.resolve();
                });
                return self.linkedin_def.promise();
            });
        },
        test_api_key: function() {
            var self = this;
            if (this.api_key) {
                return $.when();
            }
            return new instance.web.Model("ir.config_parameter").call("get_param", ["web.linkedin.apikey"]).pipe(function(a) {
                if (!!a) {
                    self.api_key = a;
                    return true;
                } else {
                    return $.Deferred().reject();
                }
            });
        },
        test_authentication: function() {
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
            this.display_dm.add(instance.web_linkedin.tester.test_linkedin()).then(function() {
                var pop = new instance.web_linkedin.LinkedinPopup(self, self.get("value"));
                pop.open();
                pop.on("selected", this, function(entity) {
                    self.selected_entity(entity);
                });
            }, _.bind(this.linkedin_disabled, this));
        },
        linkedin_disabled: function() {
            if (instance.connection.uid !== 1) {
                instance.web.dialog($(QWeb.render("LinkedIn.DisabledWarning")), {
                    title: _t("LinkedIn is not enabled"),
                    buttons: [
                        {text: _t("Ok"), click: function() { $(this).dialog("close"); }}
                    ]
                });
            } else {
                new instance.web_linkedin.KeyWizard(this).open();
            }
        },
        selected_entity: function(entity) {
            var self = this;
            this.create_on_change(entity).then(function(to_change) {
                self.view.on_processed_onchange({value:to_change});
            });
        },
        create_on_change: function(entity) {
            var self = this;
            var to_change = {};
            var defs = [];
            if (entity.__type === "company") {
                to_change.is_company = true;
                to_change.name = entity.name;
                to_change.photo = false;
                if (entity.logoUrl) {
                    defs.push(self.rpc('/web_linkedin/binary/url2binary',
                                       {'url': entity.logoUrl}).pipe(function(data){
                        to_change.photo = data;
                    }));
                }
                to_change.website = entity.websiteUrl;
                to_change.phone = false;
                _.each(entity.locations.values || [], function(el) {
                    to_change.phone = el.contactInfo.phone1;
                });
                var children_def = $.Deferred();
                IN.API.PeopleSearch().fields(commonPeopleFields).params({
                        "company-name" : entity.name,
                        "current-company": true,
                        "count": 25,
                    }).result(function(result) {
                        children_def.resolve(result);
                    });
                defs.push(children_def.pipe(function(result) {
                    var defs = _.map(result.people.values || [], function(el) {
                        el.__type = "people";
                        return self.create_on_change(el);
                    });
                    return $.when.apply($, defs).pipe(function() {
                        var p_to_change = _.toArray(arguments);
                        to_change.child_ids = p_to_change;
                    });
                }));
                /* TODO
                to_change.linkedinUrl = _.str.sprintf("http://www.linkedin.com/company/%d", entity.id);
                */
            } else { // people
                to_change.is_company = false;
                to_change.name = entity.formattedName;
                to_change.photo = false;
                if (entity.pictureUrl) {
                    defs.push(self.rpc('/web_linkedin/binary/url2binary',
                                       {'url': entity.pictureUrl}).pipe(function(data){
                        to_change.photo = data;
                    }));
                }
                to_change.mobile = false;
                to_change.phone = false;
                _.each(entity.phoneNumbers.values || [], function(el) {
                    if (el.phoneType === "mobile") {
                        to_change.mobile = el.phoneNumber;
                    } else {
                        to_change.phone = el.phoneNumber;
                    }
                });
                to_change.function = entity.headline;
                /* TODO
                to_change.linkedinUrl = entity.publicProfileUrl;
                */
            }
            return $.when.apply($, defs).pipe(function() {
                return to_change;
            });
        },
    });
    
    instance.web.form.widgets.add('linkedin', 'instance.web_linkedin.Linkedin');
    
    var commonPeopleFields = ["id", "picture-url", "public-profile-url",
                            "formatted-name", "location", "phone-numbers", "im-accounts",
                            "main-address", "headline"];
    
    instance.web_linkedin.LinkedinPopup = instance.web.Dialog.extend({
        template: "Linkedin.popup",
        init: function(parent, text) {
            this._super(parent, {title:_t("LinkedIn search")});
            this.text = text;
            this.limit = 15;
        },
        start: function() {
            this._super();
            var self = this;
            this.on("authentified", this, this.authentified);
            instance.web_linkedin.tester.test_authentication().then(function() {
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
            IN.API.PeopleSearch().fields(commonPeopleFields).
                params({"keywords": this.text, "count": this.limit}).result(function(result) {
                pdef.resolve(result);
            });
            return $.when(cdef, pdef).then(function(companies, people) {
                var lst = companies.companies.values || [];
                var plst = people.people.values || [];
                lst = _.initial(lst, _.min([self.limit / 2, plst.length]));
                _.map(lst, function(el) {
                    el.__type = "company";
                    return el;
                });
                plst = _.first(plst, self.limit - lst.length)
                _.map(plst, function(el) {
                    el.__type = "people";
                    return el;
                });
                lst = plst.concat(lst);
                console.log("Linkedin search found:", lst.length, lst);
                self.result = lst;
                self.display_result();
            });
        },
        display_result: function() {
            var self = this;
            var i = 0;
            var $row;
            _.each(self.result, function(el) {
                var pc = new instance.web_linkedin.EntityWidget(self, el);
                if (i % 5 === 0) {
                    $row = $("<div style='display: table-row;width:100%'/>");
                    $row.appendTo(self.$(">div"));
                }
                pc.appendTo($row);
                pc.$element.css("display", "table-cell");
                pc.$element.css("width", "20%");
                pc.on("selected", self, function(data) {
                    self.trigger("selected", data);
                    self.destroy();
                });
                i++;
            });
            if (self.result.length === 0) {
                self.$(">div").text(_t("No results found"));
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
            this.$element.click(function() {
                self.trigger("selected", self.data);
            });
            if (this.data.__type === "company") {
                this.$("h3").text(this.data.name);
                self.$("img").attr("src", this.data.logoUrl);
            } else { // people
                this.$("h3").text(this.data.formattedName);
                self.$("img").attr("src", this.data.pictureUrl);
            }
        },
    });
    
    
    instance.web_linkedin.KeyWizard = instance.web.Dialog.extend({
        template: "LinkedIn.KeyWizard",
        init: function(parent, text) {
            this._super(parent, {title:_t("LinkedIn API Key")});
        },
        start: function() {
            this._super();
            var self = this;
            this.$("button").click(function() {
                var value = self.$("input").val();
                debugger;
                return new instance.web.Model("ir.config_parameter").call("set_param", ["web.linkedin.apikey", value]).pipe(function() {
                    self.destroy();
                });
            });
        },
    });
};
// vim:et fdc=0 fdl=0:
