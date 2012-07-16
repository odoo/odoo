/*---------------------------------------------------------
 * OpenERP web_linkedin (module)
 *---------------------------------------------------------*/

openerp.web_linkedin = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    instance.web.form.widgets.add(
        'Linkedin', 'instance.web_linkedin.Linkedin');
    instance.web_linkedin.Linkedin = instance.web.form.FieldChar.extend({
        template: 'Linkedin',
        isAuthorized: false,
        render_value: function() {
            this._super();
            var self = this;
            this.$element.find('#loader').hide();
            if (!this.get("effective_readonly")) {
                this._super();
                self.user = new instance.web.DataSetSearch(self, 'res.users', null, null)
                .read_slice(['id','name','company_id'], {"domain": [['id','=',self.session.uid]]}).then(function(results) {
                    self.company_id = results[0].company_id[0];
                    self.company = new instance.web.DataSetSearch(self, 'res.company', null, null)
                    .read_slice(['linkedin_api_key','name'], {"domain": [['id','=',self.company_id]]}).then(function(records) {
                        self.apikey = records[0].linkedin_api_key;
                        if (self.apikey) {
                            self.add_ldn_script(self.apikey);
                        }
                    });
                });
                self.linkedin_icon_color();
                this.notification = new instance.web.Notification(this);
                this.notification.appendTo(this.$element);
                this.$element.find(".linkedin_icon").click( this.do_load_linkedin );
                this.removeTemplate();
                if(this.get('value') != false){
                    /* if value get then display button of profile url */
                    if (this.view.fields['profile_id'].get_value() || this.view.datarecord['profile_id']) {
                        this.setTemplate(this.view.datarecord['profile_id'] ,  false );
                    }
                    /* if value get then display button of twitter */
                    if (this.view.fields['twitter_id'].get_value() || this.view.datarecord['twitter_id']) {
                        this.setTemplate( false, this.view.datarecord['twitter_id']);
                    }
                }
                if (this.view.datarecord['linkedin_id']) {
                    if (this.view.datarecord['profile_id'] && !this.view.datarecord['twitter_id']) {
                        if (this.$element.find('#twitterid')) {
                            this.$element.find('#twitterid').remove();
                        }
                    }
                    else if (!this.view.datarecord['profile_id'] && this.view.datarecord['twitter_id']) {
                        if (this.$element.find('#profileid')) {
                            this.$element.find('#profileid').remove();
                        }
                    }
                }else{
                    this.removeTemplate();
                }
            } else {
                this.removeTemplate();
                if(this.get('value') != false){
                    var tagtr = document.createElement('tr');
                    tagtr.id = "profiletwittor-tr";
                    this.$element.append(tagtr);
                    /* if value get then display button of profile url */
                    if (this.view.fields['profile_id'] && this.view.datarecord['profile_id']) {
                        this.setTemplate( this.view.datarecord['profile_id'] ,  false );
                    }
                    /* if value get then display button of twitter */
                    if (this.view.fields['twitter_id'] && this.view.datarecord['twitter_id']) {
                        this.setTemplate( false, this.view.datarecord['twitter_id'] );
                    }
                }
            }
        },
        /* Load Linkedin Data On search */
        do_load_linkedin: function( e ) {
            var self = this;
            this.msg_Counter=0; /* used to display notification, when record not found on Linkedin search */
            this.removeTemplate( 1 );
            if (this.apikey){
                if (IN.ENV.auth) {
                    if (IN.ENV.auth.api_key != this.apikey){
                        return false;
                    }
                }else{
                    return false;
                }
                if (IN.ENV.auth.oauth_token) {
                    if (self.$element.find("input").val()) {
                        self.$element.find('#loader').show();
                        $('.linkedin_icon').css('display', 'none');
                        var firstNames = [];
                        var lastNames = [];
                        var text = self.$element.find("input").val().split(' ');
                        /* People Search */
                        if (text.length == 2) {
                            firstNames.push(text[0]);
                            lastNames.push(text[1]);
                            IN.API.Raw("/people-search:(people:(id,first-name,last-name,picture-url,public-profile-url,formatted-name,location,phone-numbers,im-accounts,main-address,headline))")
                            .params({
                                "first-name": firstNames[0],
                                "last-name": lastNames[0],
                                "count" : 4
                            })
                            .result( self.do_fetch_detail );
                            IN.API.Raw("/people-search:(people:(id,first-name,last-name,picture-url,public-profile-url,formatted-name,location,phone-numbers,im-accounts,main-address,headline))")
                            .params({
                                "first-name": lastNames[0],
                                "last-name": firstNames[0],
                                "count" : 4
                            })
                            .result( self.do_fetch_detail );
                        } else {
                            IN.API.Raw("/people-search:(people:(id,first-name,last-name,picture-url,public-profile-url,formatted-name,location,phone-numbers,im-accounts,main-address,headline))")
                            .params({
                                "first-name": self.$element.find("input").val(),
                                "count" : 4
                            })
                            .result( self.do_fetch_detail );
                            IN.API.Raw("/people-search:(people:(id,first-name,last-name,picture-url,public-profile-url,formatted-name,location,phone-numbers,im-accounts,main-address,headline))")
                            .params({
                                "last-name": self.$element.find("input").val(),
                                "count" : 4
                            })
                            .result( self.do_fetch_detail );
                        }
                        /* Company Search */
                        IN.API.Raw("/company-search:(companies:(id,name,description,industry,logo-url,website-url,locations,twitter-id))")
                        .params({
                            "keywords": self.$element.find("input").val(),
                            "count" : 4
                        })
                        .result( self.do_fetch_detail );
                    }else{
                        this.notification.warn(_t("Linkedin Search"), _t("Please Enter Required Field."));
                    }
                }
                else {
                    self.do_authorize();
                }
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
            } else {
                this.APIKeyWarning();
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                return false;
            }
        },
        do_authorize: function(resultCallback){
            this.check_authorized();
            if (this.isAuthorized == false){
                IN.User.authorize(resultCallback);
            }
        },
        check_authorized: function(){
            this.isAuthorized = IN.User.isAuthorized();
        },
        APIKeyWarning: function(e) {
            var self = this;
            this.dialog = instance.web.dialog($(QWeb.render("Register.Linkedin")), {
                title: _t("Connect to LinkedIn"),
                modal: true,
                width : 700, 
                height:500,
                close: function(){ self.dialog.remove();},
                buttons:[
                {
                    text: _t("Cancel"),
                    click: function() { self.dialog.remove(); }
                }]
            });
            $("#register").click(function() {
                var key = $("#apikey").val();
                if(key){
                    //self.apikey = key;
                    self.add_ldn_script(key);
                    var user = new instance.web.DataSet(self, "res.users");
                    user.call("set_linkedin_api_key", [key]);
                    self.dialog.remove();
                    //self.__parentedParent.reload();
                }
                else {
                    $("#apikey").css({'background-color':'#F66 '})
                    self.notification.warn(_t("Linkedin Search"), _t("Please Enter Required Key."));
                }
                
            })
        },
        setTemplate: function( URL, AccountName ) {
            if(AccountName){
                var AccountName = AccountName.replace(/[^a-zA-Z 0-9]+/g, '');
                Twitt = "https://twitter.com/intent/follow?original_referer=http%3A%2F%2Flocalhost%3A8069%2Fweb%2Fwebclient%2Fhome&screen_name="+AccountName+"&source=followbutton&variant=2.0"
               this.$element.find('tr#profiletwittor-tr').append(QWeb.render('TwitterURL',{'URLID': Twitt, 'account': AccountName}))
            }else if(URL){
                this.$element.find('tr#profiletwittor-tr').append(QWeb.render('ProfileURL',{'URLID': URL }))
            }
        },
        removeTemplate: function( flag ) {
            if (flag) {
                this.$element.find('#searchresults').remove();
            } else {
                if (this.$element.find('#profileid')) {
                    this.$element.find('#profileid').remove();
                }
                if (this.$element.find('#twitterid')) {
                    this.$element.find('#twitterid').remove();
                }
            }
         },
        /* Fetch Result from Linkedin and set in searchbox */
        do_fetch_detail: function(result, metadata) {
            var self = this;
            if (result.people) {
                if (result.people._total==0) {
                    this.msg_Counter++;
                }
                var count = 0;
                for (i in result.people.values) {
                    var temp = self.validName(result.people.values[i].firstName, result.people.values[i].lastName)
                    if (temp) {
                        count++;
                    }
                }
                if (count == 4 || count==result.people._total) {
                    result.people._total = 0;
                }
                this.resultcontact = result;
            }else if (result.companies) {
                if (result.companies._total == 0) {
                    this.msg_Counter++;
                }
                this.resultcompany = result;
            }
            this.removeTemplate( 1 );
            if (this.msg_Counter == 3) {
                this.notification.warn(_t("Linkedin Search"), _t("Record Not Found."));
                this.$element.find('#loader').hide();
                self.linkedin_icon_color();
            } else {
                if (this.resultcontact || this.resultcompany) {
                    this.$element.find('#linkedin-field-name').append(QWeb.render( 'Linkedincontact', {'result' : this.resultcontact, 'resultcompany' : this.resultcompany})) ;
                }
            }
            if(this.$element.find('#searchresults .search-box ul li')){
                this.$element.find('#loader').hide();
                self.linkedin_icon_color();
            }
            this.$element.find('#searchresults .search-box ul li').click( function() {
                self.getdata( this );
            });
            $(document).click( function() {
                self.removeTemplate( 1 );
            });
        },
        /* Selected record's data fetched */
        getdata: function( e ) {
            var self = this;
            if (this.resultcontact) {
                for (i in this.resultcontact.people.values) {
                    if (self.resultcontact.people.values[i].id == $(e).attr('id')) {
                        self.removeTemplate( 1 );
                        this.getTwitterAccount( self.resultcontact.people.values[i] )
                    }
                }
            }
            if(this.resultcompany){
                for ( i in this.resultcompany.companies.values ) {
                    if ( self.resultcompany.companies.values[i].id == $(e).attr('id') ) {
                        self.removeTemplate( 1 );
                        self.map_values(self.resultcompany.companies.values[i]);
                    }
                }
            }
        },
        /* Based on Linkedin Id of record fetch Twitter Account Detail for People */
        getTwitterAccount: function( values, flag, mainfield ){
            var self = this;
            IN.API.Profile(values.id).fields('twitter-accounts')
            .result(function(acname){
                values.twitterAccounts = acname.values[0].twitterAccounts
                if(flag){
                    self.map_values(values, flag, mainfield);
                }else{
                    self.map_values(values);
                }
            });
        },
        /* Mapping of Linkedin Fields with res.partner Fields
           linkedinrecord : contains linkedin record's data
           flag : indicates mapping of People search record or for company's contacts/connections (people)
            if(flag) mapping for contacts of company
            if(!flag) mapping for people search
            mainfield : class of child_ids field
        */
        map_values: function (linkedinrecord, flag, mainfield){
            var self = this, tempdata = {}, temp_data = 0, id = this.view.datarecord.id;
            _(this.view.fields).each(function (field, f) {
                if (f=='name') {
                    if (!flag) {
                        if (linkedinrecord.formattedName) {
                            field.set_value(linkedinrecord['formattedName'] || false);
                        } else if(linkedinrecord.name) {
                            field.set_value(linkedinrecord['name'] || false);
                        }
                    } else {
                        tempdata[f] = linkedinrecord.firstName+' '+linkedinrecord.lastName;
                    }
                }
                else if (f=='property_account_payable') {
                    if(flag == 1)tempdata[f] = field.get_value()
                }
                else if (f=='property_account_receivable') {
                    if(flag == 1)tempdata[f] = field.get_value()
                }
                else if (f=='type') {
                    (flag == 1) ? tempdata[f] = field.get_value() : field.get_value();
                }
                else if (f=='linkedin_id') {
                    (flag == 1) ? tempdata[f] = linkedinrecord['id'] : field.set_value(linkedinrecord['id']);
                }
                else if (f=='profile_id') {
                    if (linkedinrecord.publicProfileUrl) {
                        (flag == 1) ? tempdata[f] = linkedinrecord.publicProfileUrl : field.set_value(linkedinrecord.publicProfileUrl);
                    } else {
                        field.set_value(false);
                        tempdata[f] = false;
                    }
                }
                else if (f=='twitter_id') {
                    if (linkedinrecord.twitterAccounts && linkedinrecord.twitterAccounts._total >= 1) {
                        (flag == 1) ? tempdata[f] = linkedinrecord.twitterAccounts.values[0].providerAccountName : field.set_value(linkedinrecord.twitterAccounts.values[0].providerAccountName);
                    }else if (linkedinrecord.twitterId) {
                        (flag == 1) ? tempdata[f] = linkedinrecord.twitterId : field.set_value(linkedinrecord.twitterId);
                    } else {
                        (flag == 1) ? tempdata[f] = false : field.set_value(false);
                    }
                }
                else if (f=='mobile') {
                    if (!flag && linkedinrecord.phoneNumbers && linkedinrecord['phoneNumbers']._total>=1 && linkedinrecord['phoneNumbers'].values[0].phoneType == "mobile") {
                        field.set_value( linkedinrecord['phoneNumbers'].values[0].phoneNumber || false );
                    }else if (flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='phone') {
                    if (!flag && linkedinrecord.phoneNumbers && linkedinrecord['phoneNumbers']._total>=1 && linkedinrecord['phoneNumbers'].values[0].phoneType != "mobile") {
                        field.set_value(linkedinrecord['phoneNumbers'].values[0].phoneNumber || false);
                    } else if(flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='email') {
                    if (!flag && linkedinrecord.imAccounts && linkedinrecord['imAccounts']._total>=1) {
                        field.set_value(linkedinrecord['imAccounts'].values[0].imAccountName);
                    } else if(flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='photo') {
                    if (!flag) {
                        if (linkedinrecord.pictureUrl && linkedinrecord['pictureUrl']) {
                            /* Fetch binary data from URL for People */
                            self.rpc('/web_linkedin/binary/url2binary',{'url':linkedinrecord['pictureUrl']},function(data){
                                field.set_value(data);
                            });
                        } else if (linkedinrecord.logoUrl && linkedinrecord['logoUrl']) {
                            /* Fetch binary data from URL for Company */
                            self.rpc('/web_linkedin/binary/url2binary',{'url':linkedinrecord['logoUrl']},function(data){
                                field.set_value(data);
                            });
                        } else {
                            field.set_value(false);
                        }
                    }
                    else{
                        if (linkedinrecord['pictureUrl']) {
                            temp_data = 1;
                            /* Fetch binary data from URL for contact of Company */
                            self.rpc('/web_linkedin/binary/url2binary',{'url':linkedinrecord['pictureUrl']}).done(function(res){
                                tempdata[f] = res;
                                self.set_o2mdata(tempdata,mainfield)
                            });
                        } else {
                            tempdata[f] = "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz AAAFMQAABTEBt+0oUgAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAn6SURB VGiB1VpNjFxHEf6qf97vzGw2q921VybGJLYsRxHCxgsEiViKhBQhLpEspEggAQcOKAcQd+ML4hAp EiFHLgTlEB+TcCFAEvGTSEBIfEgcNspaylq7sb0/np/3091VHPY9MrY3xvEMimip9Hrm9av6vtfV Vd01QyKC/+dm/hdKz507t1BV1ZeJ6Igxpm+tfXNtbe3vjz/+uJu2LZrmDDzzzDNfLYri2865WCkV kiSROI5hrdVaayKitaIofv7YY48NpmVzKgSeeOKJZHZ29kdlWR4GUAIo0jStsiwLcRxTHMfWWpsC SJ1zpizL3zz66KO/n9gwADUNJXNzcz91zt2rtd4B8KFS6pLWes0Y80Ecxx+kabrW6XTWu93u1U6n U+Z5/p3nn3/+oWnYnpjAs88+e3o0Gs0z84619nIUResANojoQwCXieiy1vrDKIrWsyzbiKJo0xhT APjOk08+GU1qf6JF/PTTT/e01o8AGPb7/a3BYHBlZmZmm4gKEXEhBHHOoaoqDaDSWgfnHImIIaK5 gwcP/gTAzz41AsaYL3jvw9WrVweHDx++NjMz019bWxttbGxUURTx4uKiWGsRQgjOOR6NRhRCsCGE DECnLMuDk9ifmIC19vObm5vuoYceKhYWFkbW2uL+++93Sqlw/vx5uXDhAobDIe6+++6QJAmMMZVS arS9vT3UWhchhLmnnnrKThJeJ80DB2dnZ/3c3FytlKqVUkFrHbTWcvz4cTl58mQ7jgCwiHhmrgeD Qf3qq6/WxhiOoug+AG/fKYCJFjEzd/M8Z6WUJ6KglApKKRARiAgi0vZlTEKe5/7IkSOhKArudruH J8EwEQEiQp7nACBKKW7AS3uPiHaNKIX2XiO8b98+9t5j0jw0EQFjTDk7O9sC23NM+/0YIQHAcRxL p9NBFEVXJsFwxwReeeWV491ud9jMwHVg92pjb5paWVpa4oWFhW/dKQZgshlI7rnnnm6SJKrRo8bA /aeJSCskIu04A0AfOHDAY4IFDExAoNPp/KOu667WWgOIRMSIiG4JjAFvwZOIaBGxzfjIe58Q0euf CoETJ06UIYS3G7dJAaREFAHQ9FEbd6v2zScAMhFJqqrijY2NNz8VAgAQQvjtcDjcFpFcRDohhISZ rYgoZkYj1Ihm5khEshBCzswxMz99+vRp/tQInDp16i0Avw4hZMzcDSF0QghRA7YFDmZWzGyYOWHm PISQe+8/WF5e/uck9icmAAAnT5684L3fZuZOQyANIYzPAjGzCiFYZk4b8Akzvzap7akQAACl1Gve +4yZc+996pyzIQTNzBRCoKZvQwiJcy4tyzIKIfxpKranoaSqqj/UdW2YOWvecuS9V9571RBQ3nvr nItDCPH6+vrOsWPHimnYngqB5eXlazs7O5e890nrQt577b2H954aMiaEEG1vb9t+v/+3adgFpkQA AKIoeuvSpUvWe2+bPb9q3jw1M6Gdc+b99983WZZNlLzG29TKKlmWXRyNRoqZDQDFzIqaJNBc9crK il5YWKDBYPDOtOxOjQAz14cOHaKVlRVYa9Xi4iLa3WZVVVhZWcH8/Dzm5+fp1KlT5bTsTo2AMYbz PMfRo0dx5coVXl1dxebmJpgZcRxj//790hwxp1oKnBoBa+0BrbVPksQtLi4GrTUnSSLOOVhrudvt emutIyJ//vz5Qw888MD707A7tUXc6XS+obWuiKgkIkdEgYi4kUBETkRKIiqzLPv+tOxOTKAoivn1 9fXv5nmuAFwTkSEzVyISmFkASNMvAQzSNO3Pzc3NFkXxvaqqlia1f8cutLW19cWqqr5urT3U6/WK 0Wh01Vq76b3vO+cq730IIQgACSEEZq7jOO7neR4ppcgY8/kQwpeHw+EqM/+x2+2+DuATb+w+UW20 3+/POOcecc59SWvd0VqXIjIKIVwLIWwbY3aUUgMiKsqydGVZilIKURRRkiRWRBJrbSdJkhkAMyLS BZABSJh5pJR6zTn3uzzPt6ZKYGtr6/7RaPRNrfXn0jRlIiqMMSMRGWqtB0Q0IKIRM4+01lVd115E uNEtRERaa6W1Ns2ZIQWQN+A7zXY8E5EUgCGiCyLyUpIkb01MYHV19QcAvtLpdEpr7VBrPVBKDYlo CGCklCqIqARQA/BEFPCRK4wrJ3x09LSNxCLSHnByALmIdESkQ0SJiPw1TdNf4RaudUsCq6urP/Te n+j1eoMkSXYA7BDRQGs91FqXRFSLiCMiLyJMRNyA/jil7fFMN0Q0dtdhJCJJMwsd7LrXXUTUFZE3 siz75cdh/NhFvLGxcbSu6+O9Xm9grb2ilLoaQrhmjBkZY2oADkDYA/StplQaEmFMHICaiCoAhYgU ACoAQUQIwPHhcPiFPM/f+EQEiqJ4NM9zF0XRDhFdBbBpjBlqrWsAvgHDANoK3O1Gg/FxPHYNROQA OBEJLb4QgtVafwPA7RPY2NhIROSzWuuBiOyISD+EMEySpALgReQmH7/DCtv4Q6H5LMwM7LpXKiK5 9/5gv9/vdbvdazcq2DORlWX5tSiKyBgzAjASkYKZHRF5brTj1q5yp0RYKdW6VSEiw8Y+a60f3OvB mwisrKxYZn5Ya+2JqBKRCrvTyiICpRQaDjcVse6wXaenqSMJMwcAtYhUROSdcyfOnj17E96bvnjv vfdSEdnf+LQ0VWbdilJKe+/VWLFqWqJERDNza0u1eUR2O4fPnDkT/zcC6sCBA49EUWSJyACIsZt0 MgCZ9z4loiSEEDf32nhuGtG3Ke34/+SDRhLs+n2G3dyQikjMzEYpFa+vrz98I4HrFvHLL79MWZYd vOuuu3QURYn3vicinogsERXe+5qIHDMHZvZKKcZuBLndUEpj1/HEpgEoETHMbIkoYuYUQA/AjLU2 VUrR1tbWZ/bt23e9whujx4svvtgJIfz43nvvPTo/P19Za0fe+5GIlFrrutfr1VVV+bIsXZ7n4/F8 nMReyYxukBZ4K5aZTV3XkYhEIpJorTMRSS9duhRfvHjxjeFw+IvTp0/XtyQAAOfOnVPe+3tE5Cv3 3Xffg0tLS1mapqE5sHilVBgMBt4Y41sCRMSNr7b54cYQO169VkopaorB17lVXddaRExVVWZtbe3a 6urqnwH85Z133lk/c+bMTVuKW24lzp49q5aXl3VZlotVVT2wtLR0JMuyAzMzM71ut2uMMe1+n5vI 0W6fBQCYWZoF2pL4qOq721dNtkVd135nZ2dnMBhcXFtb+1ev13tz//79V1944QXZC/htEdhrZgDo NE11p9Ohy5cvz3rv50UkNcbEzrmYmZM4jlOlVBbHceq9BzMXzDyqqmqkta5EpGTmOkmSkfd+49ix Yzubm5v87rvvhpdeekmee+652z4XTPxfifbHvPG2V7wGgBvf5F7PftL2bxhUblkxIzmaAAAAAElF TkSuQmCC";
                        }
                    }
                }
                else if (f=='street') {
                    if (!flag && linkedinrecord.mainAddress && linkedinrecord['mainAddress']) {
                        field.set_value(linkedinrecord['mainAddress']);
                    } else if(flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='country_id') {
                    if (!flag && linkedinrecord.location && linkedinrecord['location']) {
                        field.field.domain = [['code', '=', linkedinrecord['location'].country['code'].toUpperCase()]];
                        (new instance.web.DataSetSearch(self, field.field.relation,field.field.context,field.field.domain)).read_slice(['id','name'],{}).then(function(res){
                            field.original_value = [res[0].id, res[0].name];
                            field.set_value(res[0].id)
                        })
                    } else if (!flag && linkedinrecord.locations && linkedinrecord.locations._total>0) {
                        if (linkedinrecord.locations.values[0].address['country-code']) {
                            field.field.domain = ['code', '=', linkedinrecord.locations.values[0].address['country-code'].toUpperCase()];
                            (new instance.web.DataSetSearch(self, field.field.relation,field.field.context,field.field.domain)).read_slice(['id','name'],{}).then(function(res){
                                field.original_value = [res[0].id, res[0].name];
                                field.set_value(res[0].id)
                            })
                        } else {
                            field.set_value(false);
                        }
                    } else if(flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='city') {
                    if (!flag && linkedinrecord.location && linkedinrecord['location']) {
                        field.set_value(linkedinrecord['location'].name.split(' ')[0] || false);
                    } else if (!flag && linkedinrecord.locations && linkedinrecord.locations._total>0) {
                        if (linkedinrecord.locations.values[0].address['city']) {
                            field.set_value(linkedinrecord.locations.values[0].address['city']);
                        } else {
                            field.set_value(false);
                        }
                    } else if (flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='website') {
                    if (!flag && linkedinrecord.websiteUrl) {
                        field.set_value(linkedinrecord['websiteUrl'] || false);
                    } else if (flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='customer') {
                    if(flag == 1)tempdata[f] = true;
                }
                else if (f=='supplier') {
                }
                else if (f=='active') {
                    (flag == 1) ? tempdata[f] = true : field.set_value(true);
                }
                else if (f=='is_company') {
                    if (!flag && linkedinrecord.formattedName) {
                        field.set_value(false);
                    } else {
                        field.set_value(true);
                        tempdata[f] = false;
                    }
                }
                else if (f=='zip') {
                    if (!flag && linkedinrecord.locations && linkedinrecord.locations._total>0) {
                        if (linkedinrecord.locations.values[0].address['postalCode']) {
                            field.set_value(linkedinrecord.locations.values[0].address['postalCode']);
                        } else {
                            field.set_value(false);
                        }
                    }else if (flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='parent_id') {
                    if (!flag && linkedinrecord.formattedName) {
                        field.set_value(false);
                    } else if (!flag && linkedinrecord.name) {
                        field.set_value(false);
                    } else {
                        if (linkedinrecord.formattedName) {
                            tempdata[f] = [id,self.view.fields['name'].get_value()];
                        }
                    }
                }
                else if (f=='fax') {
                    if (!flag && linkedinrecord.locations && linkedinrecord.locations._total>0) {
                        if (linkedinrecord.locations.values[0].contactInfo['fax']) {
                            field.set_value(linkedinrecord.locations.values[0].contactInfo['fax']);
                        } else {
                            field.set_value(false);
                        }
                    } else if (flag == 1) {
                        tempdata[f] = field.get_value();
                    } else {
                        field.set_value(false);
                    }
                }
                else if (f=='use_parent_address') {
                    (flag == 1) ? tempdata[f] = true : field.set_value(false);
                }
                else if (f=='child_ids') {
                    /* For Company Set value of child_ids field */
                    if (!flag && linkedinrecord.name) {
                        self.$element.find('#loader').show();
                        $('.linkedin_icon').css('display', 'none');
                        /* Fetch contact of Company */
                        IN.API.Raw("/people-search:(people:(id,first-name,last-name,formatted-name,picture-url,publicProfileUrl,phone-numbers,im-accounts,main-address,location,relation-to-viewer:(related-connections)))")
                        //"id", "firstName", "lastName", "pictureUrl", "publicProfileUrl", "formatted-name", "headline", "location", "industry", "languages", "phone-numbers", "im-accounts", "main-address"
                        .params({
                            "company-name" : linkedinrecord.name,
                            "current-company": true,
                            "count" : 25
                        })
                        .result( function (getresult){
                            if(getresult.people._total==0){
                                self.$element.find('#loader').hide();
                                if(self.view.fields['linkedin_id']){
                                    if(self.view.datarecord['linkedin_id']){
                                        self.$element.find('#linkedindefault').hide();
                                        self.$element.find('#linkedinrecord').show();
                                    }else{
                                        self.$element.find('#linkedinrecord').hide();
                                        self.$element.find('#linkedindefault').show();
                                    }
                                }
                            }
                            self.totalids = [],self.updteids = [];
                            _(field.dataset.ids).each( function(i) {
                                if (typeof(i)=="number") {
                                    self.totalids.push(i);
                                    var mobile = self.view.fields['mobile'].get_value();
                                    var phone = self.view.fields['phone'].get_value();
                                    var email = self.view.fields['email'].get_value();
                                    var fax = self.view.fields['fax'].get_value();
                                    var website = self.view.fields['website'].get_value();
                                    var zip = self.view.fields['zip'].get_value();
                                    var city = self.view.fields['city'].get_value();
                                    var country_id = self.view.fields['country_id'].get_value();
                                    var street = self.view.fields['street'].get_value();
                                    field.dataset.write(i,{'mobile':mobile,'phone':phone,'email':email,'fax':fax,'website':website,'zip':zip,'city':city,'country_id':country_id,'street':street},{});
                                }
                            });
                            field.dataset.ids = self.totalids;
                            var counter = 0;/* Indicates All searched records are Invalid or valid */
                            self.t_count=0;
                            self.o2m_count = 0;
                            for (i in getresult.people.values) {
                                var connectTemp = self.validName(getresult.people.values[i].firstName, getresult.people.values[i].lastName)
                                if (connectTemp) {
                                    counter++;
                                } else {
                                    self.t_count++;
                                    self.getTwitterAccount(getresult.people.values[i], 1, field);
                                }
                            }
                            if (getresult.people._count) {
                                var total_Count = getresult.people._count;
                            }else if (getresult.people._total) {
                                var total_Count = getresult.people._total;
                            }
                            /* If counter == total no. of people then all searched records are invalid */
                            if (counter == total_Count) {
                                field.dataset.to_create = [];
                                field.dataset.ids = [];
                                field.reload_current_view();
                            }else if(getresult.people._total == 0 || getresult.people._count == 0){
                                field.dataset.ids = self.totalids;
                                field.reload_current_view();
                            }
                        });
                    }
                    /* For People Set value of child_ids field */
                    else if (!flag && linkedinrecord.formattedName) {
                        field.set_value(false);
                        field.set({'invisible':true});
                    }
                    /* For Contact of company Set value of child_ids field */
                    else {
                        tempdata[f] = false;
                    }
                }
                else {
                    (flag == 1) ? tempdata[f] = false : field.set_value(false);
                }
                field._dirty_flag = true;
                field.on('changed_value', self, function() {
                    if (!flag) {
                        self.view.do_onchange(field);
                        self.view.on_form_changed(true);
                        self.view.do_notify_change();
                    }
                });
            });
            if (!flag) {
                this.removeTemplate();
                if (linkedinrecord.publicProfileUrl) {
                    this.setTemplate( linkedinrecord.publicProfileUrl ,  false );
                }
                if (linkedinrecord.twitterId) {
                    this.setTemplate( false ,  linkedinrecord.twitterId );
                }
                if (linkedinrecord.twitterAccounts && linkedinrecord.twitterAccounts._total >= 1) {
                    this.setTemplate( false ,  linkedinrecord.twitterAccounts.values[0].providerAccountName );
                }
            }
            if (flag && temp_data == 0) {
                self.set_o2mdata(tempdata, mainfield);
            }
         },
         /* Update existing value of child_ids field */
         set_childids: function( ids ) {
            var self = this;
            _(ids).each(function(i){
                self.view.fields['child_ids'].dataset.set_ids(self.view.fields['child_ids'].dataset.ids.concat([i]));
                self.view.fields['child_ids'].dataset.write(i, {"parent_id":false}, {});
            });
         },
         /* Set/create o2m contacts of child_ids field */
         set_o2mdata: function(data,field){
            var self = this;
            self.o2m_count++;
            field.dataset.create(data).then( function(r) {
                self.totalids.push(r.result);
                field.dataset.set_ids(field.dataset.ids.concat([r.result]));
                field.dataset.on_change();
            }).then();
            field.dataset.ids = self.totalids;
            field.reload_current_view();
            if (self.t_count == self.o2m_count) {
                self.$element.find('#loader').hide();
                self.linkedin_icon_color();
            }
         },
         /* Name of Searched Linkedin Record is valid or Not */
         validName: function(fname, lname){
            if ((fname == "Private" || fname == "private") || (lname == "Private" || lname == "private") || (fname == "" && lname == "")) {
                return true;
            } else {
                return false;
            }
         },
         // Linkedin icon color changed to distinguise record based on linkedin or not.
         linkedin_icon_color: function(e) {
             if(this.view.fields['linkedin_id']){
                 if(this.view.datarecord['linkedin_id']){
                     this.$element.find('#linkedindefault').hide();
                     this.$element.find('#linkedinrecord').show();
                 }else{
                     this.$element.find('#linkedinrecord').hide();
                     this.$element.find('#linkedindefault').show();
                 }
             }
         },
         // Add script of linkedin lib in head
         add_ldn_script: function(key){
             var self = this;
             self.apikey = key;
             var head = document.head || document.getElementsByTagName('head')[0];
             var tag = document.createElement('script');
             tag.setAttribute('id', 'addedScript');
             tag.type = 'text/javascript';
             tag.src = "http://platform.linkedin.com/in.js";
             tag.innerHTML = 'api_key : '+self.apikey+'\n';
             tag.innerHTML = tag.innerHTML + 'authorize : true';
             var temp = 0;
             $(head).find('script').each( function(i,val) {
                 if ($(val).attr('src')) {
                     if ($(val).attr('src') == "http://platform.linkedin.com/in.js") {
                         temp = 1;
                     }
                 }
             });
             if (temp != 1 ) {
                 head.appendChild( tag );
             }
         }
    });
};
// vim:et fdc=0 fdl=0:
