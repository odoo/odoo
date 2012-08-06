/*---------------------------------------------------------
 * OpenERP web_linkedin (module)
 *---------------------------------------------------------*/

openerp.web_linkedin = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    
    instance.web_linkedin.LinkedinTester = instance.web.Class.extend({
        init: function() {
            this.api_key = "cxnr0l53n73x";
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
            if (this.api_key) {
                return $.when();
            }
            return new instance.web.Model("ir.config_parameter").call("get_param", ["web.linkedin.apikey"]).pipe(function(a) {
                if (a !== false) {
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
    
                /*return new instance.web.Model("ir.config_parameter").call("set_param", ["web.linkedin.apikey", "cxnr0l53n73x"]).pipe(function() {
                    return self.test_linkedin();
                });*/
    
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
            });
        },
        selected_entity: function(entity) {
            var to_change = {};
            if (entity.__type === "company") {
                to_change.name = entity.name;
            } else { //people
                to_change.name = _.str.sprintf("%s %s", entity.firstName, entity.lastName);
            }
            this.view.on_processed_onchange({value:to_change});
        },
    });
    
    instance.web.form.widgets.add('linkedin', 'instance.web_linkedin.Linkedin');
    
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
            IN.API.Raw(_.str.sprintf("company-search:(companies:(id,name,logo-url))?keywords=%s&count=%d", encodeURI(this.text), this.limit)).result(function (result) {
                cdef.resolve(result);
            });
            IN.API.PeopleSearch().fields(["id", "first-name", "last-name","picture-url"]).
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
        },
    });
    
    instance.web_linkedin.EntityWidget = instance.web.Widget.extend({
        template: "EntityWidget",
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
                this.$("h3").text(_.str.sprintf("%s %s", this.data.firstName, this.data.lastName));
                self.$("img").attr("src", this.data.pictureUrl);
            }
        },
    });
};
// vim:et fdc=0 fdl=0:
