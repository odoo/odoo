openerp.base.m2o = function(openerp) {

openerp.base.m2o = openerp.base.Controller.extend({
    init: function(element_id, model, dataset) {
        this._super(element_id, model, dataset);

        this.element =  element_id.find('input');
        this.relation = model;
        this.dataset = dataset;
        this.name = this.element.attr('name');

        this.selectedResultRow = 0;
        this.selectedResult = false;
        this.numResultRows = 0;
        this.completeDelay = 500;
        this.specialKeyPressed = false;
        this.lastKey = null;
        this.delayedRequest = null;

        this.lastTextResult = this.element.val();
        this.lastSearch = null;

        this.select_img = jQuery('#'+ this.element.attr('name') + '_select');
        if(this.select_img)
            jQuery(this.select_img).click(jQuery.proxy(this, 'select'));

        this.element.bind({
            keydown: jQuery.proxy(this, 'on_keydown'),
            keypress: jQuery.proxy(this, 'on_keypress'),
            keyup: jQuery.proxy(this, 'on_keyup')
        });
    },

    get_matched : function() {
        if(!this.relation) {
            return;
        }
        var self = this
        this.dataset.name_search(this.element.val(),  function(response) {
            var res = response.result[0];
            self.element.val(res[1]);
            self.element.attr('text', res[0]);
        });
    },

    callSearchRequest: function() {
        this.delayedRequest = null
        this.lastSearch = this.element.val();
        var s = this.element.val();
        var val = s.lastIndexOf(',') >= 0 ? s.substring(s.lastIndexOf(',') + 1).replace(/^\s+|\s+$/g, "") : s.replace(/^\s+|\s+$/g, "");
        var self = this;
        this.dataset.name_search(val, function(obj){
            self.displayResults(obj);
        });
        return true;
    },

    select : function(evt) {
            // Set the width of combo-box as per input box
            jQuery('div#autoCompleteResults_' + this.name).width(this.element.width());

            if (jQuery('div#autoCompleteResults_'+this.name).is(':visible')){
                this.select_img.attr('src', '/base/static/src/img/icons/index1.jpeg');
                jQuery('div#autoCompleteResults_'+this.name).hide();
                return false;
            } else {
                this.select_img.attr('src', '/base/static/src/img/icons/index2.jpeg');
            }
            return this.callSearchRequest();
    },

    displayResults : function(obj) {
        var self = this;
        var result = obj.result;
        var $fancyTable = jQuery('<table>', {
            "class": "autoTextTable",
            "name": "autoCompleteTable" + self.name,
            "id": "autoCompleteTable" + self.name});

        this.numResultRows = result.length;
        this.selectedResultRow = 0;

        var rowName = "autoComplete" + self.name + "_";
        var $resultsTable = jQuery('<tbody>').appendTo($fancyTable);
        jQuery.each(result, function (i, currentObject) {

            jQuery('<tr>', {
                "class": "autoTextNormalRow",
                "name": rowName + i,
                "id": rowName + i,
            }).append(jQuery('<td>', {
                'data-id':currentObject[0],
                'class': 'm2o_coplition'
            }).append(jQuery('<span>', {
                'style':'text-transform:none; white-space: nowrap',
                'title': currentObject[1],
                'text': currentObject[1]
            }))).appendTo($resultsTable);
        });
        // Swap out the old results with the newly created table
        var $resultsHolder = jQuery("#autoCompleteResults_" + self.name);
        if($resultsTable.children().length) {
            result.length > 10 ? $resultsHolder.css('height', '50%') : $resultsHolder.css('height', '');
            $resultsHolder.empty().append($fancyTable);
            $resultsHolder.show();
        } else {
            $resultsHolder.hide();
        }
        return true;
    },

    on_keypress: function(evt) {
        if (evt.which == 9 || evt.ctrlKey) {
            return true;
        }
    },

    on_keyup: function(evt) {
        if(this.specialKeyPressed || (this.element.val() == this.lastSearch)) return false;

        if (evt.which == 40) {
            if (!this.element.val().length) {
                if (this.delayedRequest) {
                    clearInterval(this.delayedRequest);
                    this.clearResults();
                    return false;
                }
            }
            if (this.delayedRequest)
                clearInterval(this.delayedRequest);

            this.delayedRequest = setTimeout(function(thisObj){
                thisObj.callSearchRequest()
            }, this.completeDelay, this);
        }
        return true;

    },

    on_keydown : function(evt) {

        var key = evt.which;
        this.lastKey = evt.which;
        this.specialKeyPressed = false;
        if(this.numResultRows > 0) {
            switch (evt.which) {
                // Enter Key
                //Single Click
                case 13:
                case 1:
                    var $selectedRow = jQuery("#autoComplete" + this.name + "_" + this.selectedResultRow);
                    this.setCompletionText($selectedRow, true);
                    this.clearResults();
                    break;

                // Escape Key
                case 27:
                    this.clearResults();
                    break;

                // Up Key
                case 38:
                    if(this.selectedResultRow > 0) this.selectedResultRow--;
                    this.updateSelectedResult();
                    break;

                // Down Key
                case 40:

                    if(this.selectedResultRow < this.numResultRows - (this.selectedResultRow == null ? 0 : 1)) {
                        if (this.selectedResultRow == null)
                            this.selectedResultRow = 0;
                        else
                            this.selectedResultRow++;
                    }
                    this.selectedResult = true;
                    this.updateSelectedResult();
                    break;

                default:
                    break;
            }
            if(evt.which == 13 || evt.which == 27 || evt.which == 38 || evt.which == 40)//
                this.specialKeyPressed = true;
        }

        if((evt.which == 8 || evt.which == 46)) {
            var value = this.element.val();
            if (value.indexOf('[') > 0) {
                this.element.val(this.lastSearch)
                evt.stopPropagation();
                evt.preventDefault();
            }
            else if (value.length == 1) {
                this.clearResults();
            }
        }
        return !this.specialKeyPressed;
     },

    updateSelectedResult: function() {

        // Set classes to show currently selected row
        for(var i = 0; i < this.numResultRows; i++) {
            var $selectedRow = jQuery('#autoComplete' + this.name + '_' + i);
            if(this.selectedResultRow == i) {
                $selectedRow.addClass("autoTextSelectedRow");
                $selectedRow.removeClass("autoTextNormalRow") ;
                if (this.selectedResult) {
                    this.setCompletionText($selectedRow);
                }
            } else {
                $selectedRow.removeClass("autoTextSelectedRow");
                $selectedRow.addClass("autoTextNormalRow") ;
            }
        }
    },

    setCompletionText: function ($selectedRow, flag) {
        var $cell = $selectedRow.find('td');
        var autoCompleteText = $cell.find('span').text();
        autoCompleteText = flag ? autoCompleteText : this.lastSearch + '[' + autoCompleteText.substring(this.lastSearch.length) + ']'
        this.element.val(autoCompleteText);
        this.lastTextResult = autoCompleteText;
    },

    clearResults: function() {
        // Hide all the results
        jQuery("#autoCompleteResults_" + this.name).hide();
        // Clear out our result tracking
        this.selectedResultRow = 0;
        this.numResultRows = 0;
        this.lastSearch = null;
    },
    })
}