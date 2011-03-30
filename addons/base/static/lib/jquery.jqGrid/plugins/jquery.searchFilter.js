/* Plugin:      searchFilter v1.2.9
 * Author:      Kasey Speakman (kasey@cornerspeed.com)
 * License:     Dual Licensed, MIT and GPL v2 (http://www.gnu.org/licenses/gpl-2.0.html)
 *
 * REQUIREMENTS:
 *    jQuery 1.3+           (http://jquery.com/)
 *    A Themeroller Theme   (http://jqueryui.com/themeroller/)
 *
 * SECURITY WARNING
 *    You should always implement server-side checking to ensure that
 *    the query will fail when forged/invalid data is received.
 *    Clever users can send any value they want through JavaScript and HTTP POST/GET.
 *
 * THEMES
 *    Simply include the CSS file for your Themeroller theme.
 *
 * DESCRIPTION
 *     This plugin creates a new searchFilter object in the specified container
 *
 * INPUT TYPE
 *     fields:  an array of field objects. each object has the following properties:
 *              text: a string containing the display name of the field (e.g. "Field 1")
 *              itemval: a string containing the actual field name (e.g. "field1")
 *              optional properties:
 *                  ops: an array of operators in the same format as jQuery.fn.searchFilter.defaults.operators
 *                       that is: [ { op: 'gt', text: 'greater than'}, { op:'lt', text: 'less than'}, ... ]
 *                       if not specified, the passed-in options used, and failting that, jQuery.fn.searchFilter.defaults.operators will be used
 *                  *** NOTE ***
 *                  Specifying a dataUrl or dataValues property means that a <select ...> (drop-down-list) will be generated
 *                  instead of a text input <input type='text'.../> where the user would normally type in their search data
 *                  ************
 *                  dataUrl: a url that will return the html select for this field, this url will only be called once for this field
 *                  dataValues: the possible values for this field in the form [ { text: 'Data Display Text', value: 'data_actual_value' }, { ... } ]
 *                  dataInit: a function that you can use to initialize the data field. this function is passed the jQuery-fied data element
 *                  dataEvents: list of events to apply to the data element. uses $("#id").bind(type, [data], fn) to bind events to data element
 *              *** JSON of this object could look like this: ***
 *               var fields = [
 *                 {
 *                   text: 'Field Display Name',
 *                   itemval: 'field_actual_name',
 *                   // below this are optional values
 *                   ops: [ // this format is the same as jQuery.fn.searchFilter.defaults.operators
 *                     { op: 'gt', text: 'greater than' },
 *                     { op: 'lt', text: 'less than' }
 *                   ],
 *                   dataUrl: 'http://server/path/script.php?propName=propValue', // using this creates a select for the data input instead of an input type='text'
 *                   dataValues: [ // using this creates a select for the data input instead of an input type='text'
 *                     { text: 'Data Value Display Name', value: 'data_actual_value' },
 *                     { ... }
 *                   ],
 *                   dataInit: function(jElem) { jElem.datepicker(options); },
 *                   dataEvents: [ // these are the same options that you pass to $("#id").bind(type, [data], fn)
 *                     { type: 'click', data: { i: 7 }, fn: function(e) { console.log(e.data.i); } },
 *                     { type: 'keypress', fn: function(e) { console.log('keypress'); } }
 *                   ]
 *                 },
 *                 { ... }
 *               ]
 *     options: name:value properties containing various creation options
 *              see jQuery.fn.searchFilter.defaults for the overridable options
 *
 * RETURN TYPE: This plugin returns a SearchFilter object, which has additional SearchFilter methods:
 *     Methods
 *         add:    Adds a filter. added to the end of the list unless a jQuery event object or valid row number is passed.
 *         del:    Removes a filter. removed from the end of the list unless a jQuery event object or valid row number is passed.
 *         reset:  resets filters back to original state (only one blank filter), and calls onReset
 *         search: puts the search rules into an object and calls onSearch with it
 *         close:  calls the onClose event handler
 *
 * USAGE
 *     HTML
 *         <head>
 *             ...
 *             <script src="path/to/jquery.min.js" type="text/javascript"></script>
 *             <link href="path/to/themeroller.css" rel="Stylesheet" type="text/css" />
 *             <script src="path/to/jquery.searchFilter.js" type="text/javascript"></script>
 *             <link href="path/to/jquery.searchFilter.css" rel="Stylesheet" type="text/css" />
 *             ...
 *         </head>
 *         <body>
 *             ...
 *             <div id='mySearch'></div>
 *             ...
 *         </body>
 *     JQUERY
 *         Methods
 *             initializing: $("#mySearch").searchFilter([{text: "Field 1", value: "field1"},{text: "Field 2", value: "field2"}], {onSearch: myFilterRuleReceiverFn, onReset: myFilterResetFn });
 *         Manual Methods (there's no need to call these methods unless you are trying to manipulate searchFilter with script)
 *             add:          $("#mySearch").searchFilter().add();     // appends a blank filter
 *                           $("#mySearch").searchFilter().add(0);    // copies the first filter as second
 *             del:          $("#mySearch").searchFilter().del();     // removes the bottom filter
 *                           $("#mySearch").searchFilter().del(1);    // removes the second filter
 *             search:       $("#mySearch").searchFilter().search();  // invokes onSearch, passing it a ruleGroup object
 *             reset:        $("#mySearch").searchFilter().reset();   // resets rules and invokes onReset
 *             close:        $("#mySearch").searchFilter().close();   // without an onClose handler, equivalent to $("#mySearch").hide();
 * 
 * NOTE: You can get the jQuery object back from the SearchFilter object by chaining .$
 *     Example
 *         $("#mySearch").searchFilter().add().add().reset().$.hide();
 *     Verbose Example
 *         $("#mySearch")      // gets jQuery object for the HTML element with id="mySearch"
 *             .searchFilter() // gets the SearchFilter object for an existing search filter
 *             .add()          // adds a new filter to the end of the list
 *             .add()          // adds another new filter to the end of the list
 *             .reset()        // resets filters back to original state, triggers onReset
 *             .$              // returns jQuery object for $("#mySearch")
 *             .hide();        // equivalent to $("#mySearch").hide();
 */

jQuery.fn.searchFilter = function(fields, options) {

    function SearchFilter(jQ, fields, options) {


        //---------------------------------------------------------------
        // PUBLIC VARS
        //---------------------------------------------------------------

        this.$ = jQ; // makes the jQuery object available as .$ from the return value


        //---------------------------------------------------------------
        // PUBLIC FUNCTIONS
        //---------------------------------------------------------------

        this.add = function(i) {
            if (i == null) jQ.find(".ui-add-last").click();
            else jQ.find(".sf:eq(" + i + ") .ui-add").click();
            return this;
        };

        this.del = function(i) {
            if (i == null) jQ.find(".sf:last .ui-del").click();
            else jQ.find(".sf:eq(" + i + ") .ui-del").click();
            return this;
        };

        this.search = function(e) {
            jQ.find(".ui-search").click();
            return this;
        };

        this.reset = function(o) {
            if(o===undefined) o = false;
            jQ.find(".ui-reset").trigger('click',[o]);
            return this;
        };

        this.close = function() {
            jQ.find(".ui-closer").click();
            return this;
        };



        //---------------------------------------------------------------
        // "CONSTRUCTOR" (in air quotes)
        //---------------------------------------------------------------

        if (fields != null) { // type coercion matches undefined as well as null


            //---------------------------------------------------------------
            // UTILITY FUNCTIONS
            //---------------------------------------------------------------

            function hover() {
                jQuery(this).toggleClass("ui-state-hover");
                return false;
            }

            function active(e) {
                jQuery(this).toggleClass("ui-state-active", (e.type == "mousedown"));
                return false;
            }

            function buildOpt(value, text) {
                return "<option value='" + value + "'>" + text + "</option>";
            }

            function buildSel(className, options, isHidden) {
                return "<select class='" + className + "'" + (isHidden ? " style='display:none;'" : "") + ">" + options + "</select>";
            }

            function initData(selector, fn) {
                var jElem = jQ.find("tr.sf td.data " + selector);
                if (jElem[0] != null)
                    fn(jElem);
            }

            function bindDataEvents(selector, events) {
                var jElem = jQ.find("tr.sf td.data " + selector);
                if (jElem[0] != null) {
                    jQuery.each(events, function() {
                        if (this.data != null)
                            jElem.bind(this.type, this.data, this.fn);
                        else
                            jElem.bind(this.type, this.fn);
                    });
                }
            }


            //---------------------------------------------------------------
            // SUPER IMPORTANT PRIVATE VARS
            //---------------------------------------------------------------

            // copies jQuery.fn.searchFilter.defaults.options properties onto an empty object, then options onto that
            var opts = jQuery.extend({}, jQuery.fn.searchFilter.defaults, options);

            // this is keeps track of the last asynchronous setup
            var highest_late_setup = -1;


            //---------------------------------------------------------------
            // CREATION PROCESS STARTS
            //---------------------------------------------------------------

            // generate the global ops
            var gOps_html = "";
            jQuery.each(opts.groupOps, function() { gOps_html += buildOpt(this.op, this.text); });
            gOps_html = "<select name='groupOp'>" + gOps_html + "</select>";

            /* original content - doesn't minify very well
            jQ
            .html("") // clear any old content
            .addClass("ui-searchFilter") // add classes
            .append( // add content
            "\
            <div class='ui-widget-overlay' style='z-index: -1'>&nbsp;</div>\
            <table class='ui-widget-content ui-corner-all'>\
            <thead>\
            <tr>\
            <td colspan='5' class='ui-widget-header ui-corner-all' style='line-height: 18px;'>\
            <div class='ui-closer ui-state-default ui-corner-all ui-helper-clearfix' style='float: right;'>\
            <span class='ui-icon ui-icon-close'></span>\
            </div>\
            " + opts.windowTitle + "\
            </td>\
            </tr>\
            </thead>\
            <tbody>\
            <tr class='sf'>\
            <td class='fields'></td>\
            <td class='ops'></td>\
            <td class='data'></td>\
            <td><div class='ui-del ui-state-default ui-corner-all'><span class='ui-icon ui-icon-minus'></span></div></td>\
            <td><div class='ui-add ui-state-default ui-corner-all'><span class='ui-icon ui-icon-plus'></span></div></td>\
            </tr>\
            <tr>\
            <td colspan='5' class='divider'><div>&nbsp;</div></td>\
            </tr>\
            </tbody>\
            <tfoot>\
            <tr>\
            <td colspan='3'>\
            <span class='ui-reset ui-state-default ui-corner-all' style='display: inline-block; float: left;'><span class='ui-icon ui-icon-arrowreturnthick-1-w' style='float: left;'></span><span style='line-height: 18px; padding: 0 7px 0 3px;'>" + opts.resetText + "</span></span>\
            <span class='ui-search ui-state-default ui-corner-all' style='display: inline-block; float: right;'><span class='ui-icon ui-icon-search' style='float: left;'></span><span style='line-height: 18px; padding: 0 7px 0 3px;'>" + opts.searchText + "</span></span>\
            <span class='matchText'>" + opts.matchText + "</span> \
            " + gOps_html + " \
            <span class='rulesText'>" + opts.rulesText + "</span>\
            </td>\
            <td>&nbsp;</td>\
            <td><div class='ui-add-last ui-state-default ui-corner-all'><span class='ui-icon ui-icon-plusthick'></span></div></td>\
            </tr>\
            </tfoot>\
            </table>\
            ");
            /* end hard-to-minify code */
            /* begin easier to minify code */
            jQ.html("").addClass("ui-searchFilter").append("<div class='ui-widget-overlay' style='z-index: -1'>&#160;</div><table class='ui-widget-content ui-corner-all'><thead><tr><td colspan='5' class='ui-widget-header ui-corner-all' style='line-height: 18px;'><div class='ui-closer ui-state-default ui-corner-all ui-helper-clearfix' style='float: right;'><span class='ui-icon ui-icon-close'></span></div>" + opts.windowTitle + "</td></tr></thead><tbody><tr class='sf'><td class='fields'></td><td class='ops'></td><td class='data'></td><td><div class='ui-del ui-state-default ui-corner-all'><span class='ui-icon ui-icon-minus'></span></div></td><td><div class='ui-add ui-state-default ui-corner-all'><span class='ui-icon ui-icon-plus'></span></div></td></tr><tr><td colspan='5' class='divider'><hr class='ui-widget-content' style='margin:1px'/></td></tr></tbody><tfoot><tr><td colspan='3'><span class='ui-reset ui-state-default ui-corner-all' style='display: inline-block; float: left;'><span class='ui-icon ui-icon-arrowreturnthick-1-w' style='float: left;'></span><span style='line-height: 18px; padding: 0 7px 0 3px;'>" + opts.resetText + "</span></span><span class='ui-search ui-state-default ui-corner-all' style='display: inline-block; float: right;'><span class='ui-icon ui-icon-search' style='float: left;'></span><span style='line-height: 18px; padding: 0 7px 0 3px;'>" + opts.searchText + "</span></span><span class='matchText'>" + opts.matchText + "</span> " + gOps_html + " <span class='rulesText'>" + opts.rulesText + "</span></td><td>&#160;</td><td><div class='ui-add-last ui-state-default ui-corner-all'><span class='ui-icon ui-icon-plusthick'></span></div></td></tr></tfoot></table>");
            /* end easier-to-minify code */

            var jRow = jQ.find("tr.sf");
            var jFields = jRow.find("td.fields");
            var jOps = jRow.find("td.ops");
            var jData = jRow.find("td.data");

            // generate the defaults
            var default_ops_html = "";
            jQuery.each(opts.operators, function() { default_ops_html += buildOpt(this.op, this.text); });
            default_ops_html = buildSel("default", default_ops_html, true);
            jOps.append(default_ops_html);
            var default_data_html = "<input type='text' class='default' style='display:none;' />";
            jData.append(default_data_html);

            // generate the field list as a string
            var fields_html = "";
            var has_custom_ops = false;
            var has_custom_data = false;
            jQuery.each(fields, function(i) {
                var field_num = i;
                fields_html += buildOpt(this.itemval, this.text);
                // add custom ops if they exist
                if (this.ops != null) {
                    has_custom_ops = true;
                    var custom_ops = "";
                    jQuery.each(this.ops, function() { custom_ops += buildOpt(this.op, this.text); });
                    custom_ops = buildSel("field" + field_num, custom_ops, true);
                    jOps.append(custom_ops);
                }
                // add custom data if it is given
                if (this.dataUrl != null) {
                    if (i > highest_late_setup) highest_late_setup = i;
                    has_custom_data = true;
                    var dEvents = this.dataEvents;
                    var iEvent = this.dataInit;
                    var bs = this.buildSelect;
                    jQuery.ajax(jQuery.extend({
                        url : this.dataUrl,
                        complete: function(data) {
                            var $d;
                            if(bs != null) $d =jQuery("<div />").append(bs(data));
                            else $d = jQuery("<div />").append(data.responseText);
                            $d.find("select").addClass("field" + field_num).hide();
                            jData.append($d.html());
                            if (iEvent) initData(".field" + i, iEvent);
                            if (dEvents) bindDataEvents(".field" + i, dEvents);
                            if (i == highest_late_setup) { // change should get called no more than twice when this searchFilter is constructed
                                jQ.find("tr.sf td.fields select[name='field']").change();
                            }
                        }
                    },opts.ajaxSelectOptions));
                } else if (this.dataValues != null) {
                    has_custom_data = true;
                    var custom_data = "";
                    jQuery.each(this.dataValues, function() { custom_data += buildOpt(this.value, this.text); });
                    custom_data = buildSel("field" + field_num, custom_data, true);
                    jData.append(custom_data);
                } else if (this.dataEvents != null || this.dataInit != null) {
                    has_custom_data = true;
                    var custom_data = "<input type='text' class='field" + field_num + "' />";
                    jData.append(custom_data);
                }
                // attach events to data if they exist
                if (this.dataInit != null && i != highest_late_setup)
                    initData(".field" + i, this.dataInit);
                if (this.dataEvents != null && i != highest_late_setup)
                    bindDataEvents(".field" + i, this.dataEvents);
            });
            fields_html = "<select name='field'>" + fields_html + "</select>";
            jFields.append(fields_html);

            // setup the field select with an on-change event if there are custom ops or data
            var jFSelect = jFields.find("select[name='field']");
            if (has_custom_ops) jFSelect.change(function(e) {
                var index = e.target.selectedIndex;
                var td = jQuery(e.target).parents("tr.sf").find("td.ops");
                td.find("select").removeAttr("name").hide(); // disown and hide all elements
                var jElem = td.find(".field" + index);
                if (jElem[0] == null) jElem = td.find(".default"); // if there's not an element for that field, use the default one
                jElem.attr("name", "op").show();
                return false;
            });
            else jOps.find(".default").attr("name", "op").show();
            if (has_custom_data) jFSelect.change(function(e) {
                var index = e.target.selectedIndex;
                var td = jQuery(e.target).parents("tr.sf").find("td.data");
                td.find("select,input").removeClass("vdata").hide(); // disown and hide all elements
                var jElem = td.find(".field" + index);
                if (jElem[0] == null) jElem = td.find(".default"); // if there's not an element for that field, use the default one
                jElem.show().addClass("vdata");
                return false;
            });
            else jData.find(".default").show().addClass("vdata");
            // go ahead and call the change event and setup the ops and data values
            if (has_custom_ops || has_custom_data) jFSelect.change();

            // bind events
            jQ.find(".ui-state-default").hover(hover, hover).mousedown(active).mouseup(active); // add hover/active effects to all buttons
            jQ.find(".ui-closer").click(function(e) {
                opts.onClose(jQuery(jQ.selector));
                return false;
            });
            jQ.find(".ui-del").click(function(e) {
                var row = jQuery(e.target).parents(".sf");
                if (row.siblings(".sf").length > 0) { // doesn't remove if there's only one filter left
                    if (opts.datepickerFix === true && jQuery.fn.datepicker !== undefined)
                        row.find(".hasDatepicker").datepicker("destroy"); // clean up datepicker's $.data mess
                    row.remove(); // also unbinds
                } else { // resets the filter if it's the last one
                    row.find("select[name='field']")[0].selectedIndex = 0;
                    row.find("select[name='op']")[0].selectedIndex = 0;
                    row.find(".data input").val(""); // blank all input values
                    row.find(".data select").each(function() { this.selectedIndex = 0; }); // select first option on all selects
                    row.find("select[name='field']").change(function(event){event.stopPropagation();}); // trigger any change events
                }
                return false;
            });
            jQ.find(".ui-add").click(function(e) {
                var row = jQuery(e.target).parents(".sf");
                var newRow = row.clone(true).insertAfter(row);
                newRow.find(".ui-state-default").removeClass("ui-state-hover ui-state-active");
                if (opts.clone) {
                    newRow.find("select[name='field']")[0].selectedIndex = row.find("select[name='field']")[0].selectedIndex;
                    var stupid_browser = (newRow.find("select[name='op']")[0] == null); // true for IE6
                    if (!stupid_browser)
                        newRow.find("select[name='op']").focus()[0].selectedIndex = row.find("select[name='op']")[0].selectedIndex;
                    var jElem = newRow.find("select.vdata");
                    if (jElem[0] != null) // select doesn't copy it's selected index when cloned
                        jElem[0].selectedIndex = row.find("select.vdata")[0].selectedIndex;
                } else {
                    newRow.find(".data input").val(""); // blank all input values
                    newRow.find("select[name='field']").focus();
                }
                if (opts.datepickerFix === true && jQuery.fn.datepicker !== undefined) { // using $.data to associate data with document elements is Not Good
                    row.find(".hasDatepicker").each(function() {
                        var settings = jQuery.data(this, "datepicker").settings;
                        newRow.find("#" + this.id).unbind().removeAttr("id").removeClass("hasDatepicker").datepicker(settings);
                    });
                }
                newRow.find("select[name='field']").change(function(event){event.stopPropagation();} );
                return false;
            });
            jQ.find(".ui-search").click(function(e) {
                var ui = jQuery(jQ.selector); // pointer to search box wrapper element
                var ruleGroup;
                var group_op = ui.find("select[name='groupOp'] :selected").val(); // puls "AND" or "OR"
                if (!opts.stringResult) {
                    ruleGroup = {
                        groupOp: group_op,
                        rules: []
                    };
                } else {
                    ruleGroup = "{\"groupOp\":\"" + group_op + "\",\"rules\":[";
                }
                ui.find(".sf").each(function(i) {
                    var tField = jQuery(this).find("select[name='field'] :selected").val();
                    var tOp = jQuery(this).find("select[name='op'] :selected").val();
                    var tData = jQuery(this).find("input.vdata,select.vdata :selected").val();
                    tData += "";
                    if (!opts.stringResult) {
                        ruleGroup.rules.push({
                            field: tField,
                            op: tOp,
                            data: tData
                        });
                    } else {
						tData = tData.replace(/\\/g,'\\\\').replace(/\"/g,'\\"');
                        if (i > 0) ruleGroup += ",";
                        ruleGroup += "{\"field\":\"" + tField + "\",";
                        ruleGroup += "\"op\":\"" + tOp + "\",";
                        ruleGroup += "\"data\":\"" + tData + "\"}";
                    }
                });
                if (opts.stringResult) ruleGroup += "]}";
                opts.onSearch(ruleGroup);
                return false;
            });
            jQ.find(".ui-reset").click(function(e,op) {
                var ui = jQuery(jQ.selector);
                ui.find(".ui-del").click(); // removes all filters, resets the last one
                ui.find("select[name='groupOp']")[0].selectedIndex = 0; // changes the op back to the default one
                opts.onReset(op);
                return false;
            });
            jQ.find(".ui-add-last").click(function() {
                var row = jQuery(jQ.selector + " .sf:last");
                var newRow = row.clone(true).insertAfter(row);
                newRow.find(".ui-state-default").removeClass("ui-state-hover ui-state-active");
                newRow.find(".data input").val(""); // blank all input values
                newRow.find("select[name='field']").focus();
                if (opts.datepickerFix === true && jQuery.fn.datepicker !== undefined) { // using $.data to associate data with document elements is Not Good
                    row.find(".hasDatepicker").each(function() {
                        var settings = jQuery.data(this, "datepicker").settings;
                        newRow.find("#" + this.id).unbind().removeAttr("id").removeClass("hasDatepicker").datepicker(settings);
                    });
                }
                newRow.find("select[name='field']").change(function(event){event.stopPropagation();});
                return false;
            });

            this.setGroupOp = function(setting) {
                /* a "setter" for groupping argument.
                 *  ("AND" or "OR")
                 *
                 * Inputs:
                 *  setting - a string
                 *
                 * Returns:
                 *  Does not return anything. May add success / failure reporting in future versions.
                 *
                 *  author: Daniel Dotsenko (dotsa@hotmail.com)
                 */
                selDOMobj = jQ.find("select[name='groupOp']")[0];
                var indexmap = {}, l = selDOMobj.options.length, i;
                for (i=0; i<l; i++) {
                    indexmap[selDOMobj.options[i].value] = i;
                }
                selDOMobj.selectedIndex = indexmap[setting];
                jQuery(selDOMobj).change(function(event){event.stopPropagation();});
            };

            this.setFilter = function(settings) {
                /* a "setter" for an arbitrary SearchFilter's filter line.
                 * designed to abstract the DOM manipulations required to infer
                 * a particular filter is a fit to the search box.
                 *
                 * Inputs:
                 *  settings - an "object" (dictionary)
                 *   index (optional*) (to be implemented in the future) : signed integer index (from top to bottom per DOM) of the filter line to fill.
                 *           Negative integers (rooted in -1 and lower) denote position of the line from the bottom.
                 *   sfref (optional*) : DOM object referencing individual '.sf' (normally a TR element) to be populated. (optional)
                 *   filter (mandatory) : object (dictionary) of form {'field':'field_value','op':'op_value','data':'data value'}
                 *
                 * * It is mandatory to have either index or sfref defined.
                 *
                 * Returns:
                 *  Does not return anything. May add success / failure reporting in future versions.
                 *
                 *  author: Daniel Dotsenko (dotsa@hotmail.com)
                 */

                var o = settings['sfref'], filter = settings['filter'];
                
                // setting up valueindexmap that we will need to manipulate SELECT elements.
                var fields = [], i, j , l, lj, li,
                    valueindexmap = {};
                    // example of valueindexmap:
                    // {'field1':{'index':0,'ops':{'eq':0,'ne':1}},'fieldX':{'index':1,'ops':{'eq':0,'ne':1},'data':{'true':0,'false':1}}},
                    // if data is undefined it's a INPUT field. If defined, it's SELECT
                selDOMobj = o.find("select[name='field']")[0];
                for (i=0, l=selDOMobj.options.length; i<l; i++) {
                    valueindexmap[selDOMobj.options[i].value] = {'index':i,'ops':{}};
                    fields.push(selDOMobj.options[i].value);
                }
                for (i=0, li=fields.length; i < li; i++) {
                    selDOMobj = o.find(".ops > select[class='field"+i+"']")[0];
                    if (selDOMobj) {
                        for (j=0, lj=selDOMobj.options.length; j<lj; j++) {
                            valueindexmap[fields[i]]['ops'][selDOMobj.options[j].value] = j;
                        }
                    }
                    selDOMobj = o.find(".data > select[class='field"+i+"']")[0];
                    if (selDOMobj) {
                        valueindexmap[fields[i]]['data'] = {}; // this setting is the flag that 'data' is contained in a SELECT
                        for (j=0, lj=selDOMobj.options.length; j<lj; j++) {
                            valueindexmap[fields[i]]['data'][selDOMobj.options[j].value] = j;
                        }
                    }
                } // done populating valueindexmap

                // preparsing the index values for SELECT elements.
                var fieldvalue, fieldindex, opindex, datavalue, dataindex;
                fieldvalue = filter['field'];
				if (valueindexmap[fieldvalue]) {
					fieldindex = valueindexmap[fieldvalue]['index'];
				}
                if (fieldindex != null) {
                    opindex = valueindexmap[fieldvalue]['ops'][filter['op']];
                    if(opindex === undefined) {
                        for(i=0,li=options.operators.length; i<li;i++) {
                            if(options.operators[i].op == filter.op ){
                                opindex = i;
                                break;
                            }
                        }
                    }
                    datavalue = filter['data'];
                    if (valueindexmap[fieldvalue]['data'] == null) {
                        dataindex = -1; // 'data' is not SELECT, Making the var 'defined'
                    } else {
                        dataindex = valueindexmap[fieldvalue]['data'][datavalue]; // 'undefined' may come from here.
                    }
                }
                // only if values for 'field' and 'op' and 'data' are 'found' in mapping...
                if (fieldindex != null && opindex != null && dataindex != null) {
                    o.find("select[name='field']")[0].selectedIndex = fieldindex;
                    o.find("select[name='field']").change();
                    o.find("select[name='op']")[0].selectedIndex = opindex;
                    o.find("input.vdata").val(datavalue); // if jquery does not find any INPUT, it does not set any. This means we deal with SELECT
                    o = o.find("select.vdata")[0];
                    if (o) {
                        o.selectedIndex = dataindex;
                    }
					return true
                } else {
					return false
				}
            }; // end of this.setFilter fn
        } // end of if fields != null
    }
    return new SearchFilter(this, fields, options);
};

jQuery.fn.searchFilter.version = '1.2.9';

/* This property contains the default options */
jQuery.fn.searchFilter.defaults = {

    /*
     * PROPERTY
     * TYPE:        boolean 
     * DESCRIPTION: clone a row if it is added from an existing row
     *              when false, any new added rows will be blank.
     */
    clone: true,

    /*
     * PROPERTY
     * TYPE:        boolean 
     * DESCRIPTION: current version of datepicker uses a data store,
     *              which is incompatible with $().clone(true)
     */
    datepickerFix: true,

    /*
     * FUNCTION
     * DESCRIPTION: the function that will be called when the user clicks Reset
     * INPUT TYPE:  JS object if stringResult is false, otherwise is JSON string
     */
    onReset: function(data) { alert("Reset Clicked. Data Returned: " + data) },

    /*
     * FUNCTION
     * DESCRIPTION: the function that will be called when the user clicks Search
     * INPUT TYPE:  JS object if stringResult is false, otherwise is JSON string
     */
    onSearch: function(data) { alert("Search Clicked. Data Returned: " + data) },

    /*
     * FUNCTION
     * DESCRIPTION: the function that will be called when the user clicks the Closer icon
     *              or the close() function is called
     *              if left null, it simply does a .hide() on the searchFilter
     * INPUT TYPE:  a jQuery object for the searchFilter
     */
    onClose: function(jElem) { jElem.hide(); },

    /* 
     * PROPERTY
     * TYPE:        array of objects, each object has the properties op and text 
     * DESCRIPTION: the selectable operators that are applied between rules
     *              e.g. for {op:"AND", text:"all"}
     *                  the search filter box will say: match all rules
     *                  the server should interpret this as putting the AND op between each rule:
     *                      rule1 AND rule2 AND rule3
     *              text will be the option text, and op will be the option value
     */
    groupOps: [
        { op: "AND", text: "all" },
        { op: "OR",  text: "any" }
    ],


    /* 
     * PROPERTY
     * TYPE:        array of objects, each object has the properties op and text 
     * DESCRIPTION: the operators that will appear as drop-down options
     *              text will be the option text, and op will be the option value
     */
    operators: [
        { op: "eq", text: "is equal to" },
        { op: "ne", text: "is not equal to" },
        { op: "lt", text: "is less than" },
        { op: "le", text: "is less or equal to" },
        { op: "gt", text: "is greater than" },
        { op: "ge", text: "is greater or equal to" },
        { op: "in", text: "is in" },
        { op: "ni", text: "is not in" },
        { op: "bw", text: "begins with" },
        { op: "bn", text: "does not begin with" },
        { op: "ew", text: "ends with" },
        { op: "en", text: "does not end with" },
        { op: "cn", text: "contains" },
        { op: "nc", text: "does not contain" }
    ],

    /*
     * PROPERTY
     * TYPE:        string
     * DESCRIPTION: part of the phrase: _match_ ANY/ALL rules
     */
    matchText: "match",

    /*
     * PROPERTY
     * TYPE:        string
     * DESCRIPTION: part of the phrase: match ANY/ALL _rules_
     */
    rulesText: "rules",

    /*
     * PROPERTY
     * TYPE:        string
     * DESCRIPTION: the text that will be displayed in the reset button
     */
    resetText: "Reset",
    
    /*
     * PROPERTY
     * TYPE:        string
     * DESCRIPTION: the text that will be displayed in the search button
     */
    searchText: "Search",
    
    /*
     * PROPERTY
     * TYPE:        boolean
     * DESCRIPTION: a flag that, when set, will make the onSearch and onReset return strings instead of objects
     */
    stringResult: true,    
    
    /*
     * PROPERTY
     * TYPE:        string
     * DESCRIPTION: the title of the searchFilter window
     */
    windowTitle: "Search Rules",
    /*
     * PROPERTY
     * TYPE:        object
     * DESCRIPTION: options to extend the ajax request
     */
    ajaxSelectOptions : {}
}; /* end of searchFilter */